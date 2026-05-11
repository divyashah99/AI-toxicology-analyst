"""Deterministic agent graph.

Nodes (in order):
  1. resolve_identity  — PubChem search/properties + RDKit canonicalize
  2. compute_descriptors — RDKit
  3. score_toxicity — heuristic toxicity server
  4. retrieve_literature — papers server (only if paper_ids supplied)
  5. synthesize — single LLM call producing the markdown brief
  6. finalize — assemble the ToxicityReport

We deliberately keep at most ONE tool of each type per turn and never re-enter
the loop. Worst case = 4-5 tool calls + 1 LLM call per analysis.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.agent.prompts import SYSTEM_PROMPT, synthesize_user_prompt
from app.agent.trace import TraceBus
from app.core.logging import get_logger
from app.mcp_client.client import McpClient
from app.models.schemas import (
    Citation,
    CompoundIdentity,
    CompoundQuery,
    Descriptors,
    RetrievedChunk,
    StructuralAlert,
    ToxicityReport,
    ToxicitySignal,
    TraceEvent,
)
from app.services import llm

log = get_logger("agent.orchestrator")


class AgentError(RuntimeError):
    pass


class Orchestrator:
    def __init__(self, mcp: McpClient) -> None:
        self.mcp = mcp

    async def run(
        self,
        *,
        query: CompoundQuery,
        paper_ids: list[str],
        bus: TraceBus,
    ) -> ToxicityReport:
        await bus.emit(
            TraceEvent(
                kind="plan",
                label="Plan",
                text=(
                    "resolve_identity → descriptors → toxicity"
                    + (" → retrieve" if paper_ids else "")
                    + " → synthesize"
                ),
            )
        )

        identity = await self._resolve_identity(query, bus)
        descriptors = await self._descriptors(identity.smiles, bus)
        tox = await self._score(identity.smiles, bus)

        # Literature retrieval — query is auto-generated from identity + alerts.
        evidence: list[dict[str, Any]] = []
        if paper_ids:
            q = self._retrieval_question(identity, tox)
            evidence = await self._retrieve(q, paper_ids, bus)

        # LLM synthesis
        await bus.emit(TraceEvent(kind="llm_call", label="synthesize report"))
        prompt = synthesize_user_prompt(
            identity=identity.model_dump(exclude_none=True),
            descriptors=descriptors.model_dump(exclude_none=True),
            toxicity=tox.model_dump(),
            evidence=evidence,
        )
        summary_md = ""
        async for delta in llm.stream(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=900,
        ):
            summary_md += delta
            await bus.emit(TraceEvent(kind="llm_chunk", label="chunk", text=delta))

        report = ToxicityReport(
            compound=identity,
            descriptors=descriptors,
            toxicity=tox,
            summary_md=summary_md.strip(),
            affected_pathways=self._extract_pathways(summary_md),
            evidence=[
                RetrievedChunk(
                    paper_id=c["paper_id"],
                    chunk_idx=c["chunk_idx"],
                    page=c["page"],
                    text=c["text"],
                    score=c["score"],
                )
                for c in evidence
            ],
            citations=[
                Citation(
                    n=i + 1,
                    paper_id=c["paper_id"],
                    page=c["page"],
                    snippet=c["text"][:240],
                )
                for i, c in enumerate(evidence)
            ],
            generated_at=datetime.utcnow(),
        )

        await bus.emit(TraceEvent(kind="done", label="report ready"))
        return report

    # ----- nodes -----

    async def _resolve_identity(
        self, q: CompoundQuery, bus: TraceBus
    ) -> CompoundIdentity:
        async def trace(ev: TraceEvent) -> None:
            await bus.emit(ev)

        # 1. Resolve CID
        cid = q.cid
        if cid is None:
            search_args = {}
            if q.name:
                search_args["name"] = q.name
            if q.smiles:
                search_args["smiles"] = q.smiles
            if not search_args:
                raise AgentError("Provide a name, SMILES, or CID.")
            res = await self.mcp.call(
                "pubchem", "search_compound", search_args, trace=trace
            )
            cid = res.get("cid")

        identity = CompoundIdentity(name=q.name, smiles=q.smiles, cid=cid)

        # 2. Properties from PubChem (best source of canonical fields)
        if cid is not None:
            try:
                props = await self.mcp.call(
                    "pubchem", "get_properties", {"cid": cid}, trace=trace
                )
                identity = identity.model_copy(
                    update={
                        "iupac_name": props.get("iupac_name"),
                        "smiles": identity.smiles or props.get("smiles"),
                        "inchi": props.get("inchi"),
                        "inchikey": props.get("inchikey"),
                        "formula": props.get("formula"),
                        "mw": props.get("mw"),
                    }
                )
            except Exception as exc:
                log.warning("pubchem.properties_failed", cid=cid, err=str(exc))

        # 3. Canonicalize via RDKit if we have a SMILES (or fall back to PubChem's)
        if identity.smiles:
            try:
                canon = await self.mcp.call(
                    "rdkit",
                    "canonicalize",
                    {"smiles": identity.smiles},
                    trace=trace,
                )
                identity = identity.model_copy(
                    update={
                        "smiles": canon["canonical_smiles"],
                        "inchi": identity.inchi or canon.get("inchi"),
                        "inchikey": identity.inchikey or canon.get("inchikey"),
                    }
                )
            except Exception as exc:
                log.warning("rdkit.canonicalize_failed", err=str(exc))

        if not identity.smiles:
            raise AgentError(
                f"Could not resolve a SMILES for input {q.model_dump(exclude_none=True)}. "
                "Try providing the SMILES directly."
            )
        return identity

    async def _descriptors(self, smiles: str, bus: TraceBus) -> Descriptors:
        async def trace(ev: TraceEvent) -> None:
            await bus.emit(ev)

        d = await self.mcp.call(
            "rdkit", "descriptors", {"smiles": smiles}, trace=trace
        )
        return Descriptors(**d)

    async def _score(self, smiles: str, bus: TraceBus) -> ToxicitySignal:
        async def trace(ev: TraceEvent) -> None:
            await bus.emit(ev)

        d = await self.mcp.call(
            "toxicity", "score", {"smiles": smiles}, trace=trace
        )
        return ToxicitySignal(
            score=d["score"],
            risk_band=d["risk_band"],
            confidence=d["confidence"],
            structural_alerts=[StructuralAlert(**a) for a in d["structural_alerts"]],
            physchem_flags=d["physchem_flags"],
        )

    async def _retrieve(
        self, question: str, paper_ids: list[str], bus: TraceBus
    ) -> list[dict[str, Any]]:
        async def trace(ev: TraceEvent) -> None:
            await bus.emit(ev)

        res = await self.mcp.call(
            "papers",
            "retrieve",
            {"question": question, "paper_ids": paper_ids, "k": 6},
            trace=trace,
        )
        return res.get("chunks", [])

    @staticmethod
    def _retrieval_question(identity: CompoundIdentity, tox: ToxicitySignal) -> str:
        names = identity.name or identity.iupac_name or identity.smiles
        alert_names = ", ".join(a.name for a in tox.structural_alerts) or "general toxicity"
        return f"Toxicity, mechanism, and adverse effects of {names}. Focus: {alert_names}."

    @staticmethod
    def _extract_pathways(md: str) -> list[str]:
        """Pull bullet items under '## Likely affected pathways'."""
        import re

        m = re.search(
            r"##\s*Likely affected pathways\s*(.+?)(?:\n##|\Z)",
            md,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return []
        lines = [
            re.sub(r"^[-*]\s+", "", ln).strip()
            for ln in m.group(1).splitlines()
            if ln.strip().startswith(("-", "*"))
        ]
        return [ln for ln in lines if ln][:8]


# Convenience runner
async def run_with_trace(
    mcp: McpClient,
    query: CompoundQuery,
    paper_ids: list[str],
) -> tuple[ToxicityReport, TraceBus]:
    bus = TraceBus()
    orch = Orchestrator(mcp)
    try:
        report = await orch.run(query=query, paper_ids=paper_ids, bus=bus)
    finally:
        await bus.close()
    return report, bus


__all__ = ["Orchestrator", "AgentError", "run_with_trace"]

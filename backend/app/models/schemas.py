"""Pydantic schemas shared across API + agent."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------- Compounds ----------


class CompoundQuery(BaseModel):
    """Either name or smiles must be provided."""

    name: str | None = None
    smiles: str | None = None
    cid: int | None = None


class CompoundIdentity(BaseModel):
    cid: int | None = None
    name: str | None = None
    iupac_name: str | None = None
    smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    formula: str | None = None
    mw: float | None = None


class Descriptors(BaseModel):
    mw: float | None = None
    logp: float | None = None
    tpsa: float | None = None
    h_donors: int | None = None
    h_acceptors: int | None = None
    rotatable_bonds: int | None = None
    aromatic_rings: int | None = None
    heavy_atoms: int | None = None
    qed: float | None = None
    lipinski_violations: int | None = None


class StructuralAlert(BaseModel):
    name: str
    smarts: str
    severity: Literal["low", "medium", "high"]
    description: str


class ToxicitySignal(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    risk_band: Literal["low", "moderate", "high"]
    confidence: float = Field(ge=0.0, le=1.0)
    structural_alerts: list[StructuralAlert] = []
    physchem_flags: list[str] = []


# ---------- Papers ----------


class PaperMeta(BaseModel):
    paper_id: str
    title: str | None = None
    filename: str
    pages: int
    chunk_count: int
    uploaded_at: datetime


class RetrievedChunk(BaseModel):
    paper_id: str
    chunk_idx: int
    page: int
    text: str
    score: float


# ---------- Reports ----------


class Citation(BaseModel):
    n: int
    paper_id: str
    page: int
    snippet: str


class ToxicityReport(BaseModel):
    compound: CompoundIdentity
    descriptors: Descriptors
    toxicity: ToxicitySignal
    summary_md: str
    affected_pathways: list[str] = []
    evidence: list[RetrievedChunk] = []
    citations: list[Citation] = []
    disclaimer: str = (
        "Heuristic + LLM-derived risk view. Not validated for clinical or "
        "regulatory use. See ARCHITECTURE.md for methodology."
    )
    generated_at: datetime


# ---------- Agent trace ----------


TraceKind = Literal[
    "intent", "plan", "tool_call", "tool_result", "llm_call", "llm_chunk", "done", "error"
]


class TraceEvent(BaseModel):
    kind: TraceKind
    label: str
    server: str | None = None
    tool: str | None = None
    args: dict[str, Any] | None = None
    output: dict[str, Any] | str | None = None
    duration_ms: int | None = None
    text: str | None = None
    ts: datetime = Field(default_factory=datetime.utcnow)


# ---------- API requests/responses ----------


class AnalyzeRequest(BaseModel):
    query: CompoundQuery
    paper_ids: list[str] = []
    stream: bool = True


class AnalyzeResponse(BaseModel):
    report: ToxicityReport
    trace: list[TraceEvent]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    paper_ids: list[str] = []

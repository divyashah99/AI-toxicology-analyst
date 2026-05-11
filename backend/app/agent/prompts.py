"""Prompt templates. Kept short to control tokens."""
from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """\
You are AI Toxicology Analyst. You write concise, scientific summaries grounded
strictly in the data provided to you. Do not invent CIDs, descriptors, or
citations. When literature evidence is given, cite it inline as [n] referencing
the supplied chunks. If a value is missing, say so explicitly. Avoid clinical
recommendations.
"""


def synthesize_user_prompt(
    *,
    identity: dict[str, Any],
    descriptors: dict[str, Any],
    toxicity: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> str:
    ev = "\n".join(
        f"[{i + 1}] (p.{c['page']}) {c['text'][:600]}"
        for i, c in enumerate(evidence)
    ) or "(no literature retrieved)"

    return f"""\
COMPOUND
{json.dumps(identity, indent=2)}

DESCRIPTORS
{json.dumps(descriptors, indent=2)}

TOXICITY SIGNALS (heuristic, not a trained model)
{json.dumps(toxicity, indent=2)}

LITERATURE EVIDENCE
{ev}

TASK
Write a structured toxicology brief in markdown with the following sections:

## Compound summary
2-3 sentences: identity, class, primary use if known.

## Risk overview
State the risk band ({toxicity['risk_band']}) and what drives it. Reference the
structural alerts and physchem flags by name.

## Likely affected pathways
Bullet list. Only include pathways supported by the alerts or the literature
evidence. If literature is silent, infer cautiously from chemistry and label
those bullets "(inferred from structure)".

## Evidence
Quote 1-2 short fragments with [n] citations. If no literature is available,
write "No supporting literature was retrieved."

## Caveats
Two bullets: (1) heuristic scoring caveat, (2) any specific limitations
(missing logP, no in vivo data in evidence, etc.).

Be terse. No preamble. ~250 words total.
"""


CLASSIFY_PROMPT = """\
You classify the user's intent into ONE of: compound_analysis, paper_qa,
full_report. Respond with strict JSON: {"intent": "..."}.

Rules:
- "compound_analysis" if they ask about a chemical (name/SMILES) without paper context.
- "paper_qa" if they ask a question and provide paper_ids (no compound).
- "full_report" if both are present, or they ask for a "report".
"""

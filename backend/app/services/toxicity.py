"""Heuristic toxicity scoring.

This is intentionally NOT a trained ML model. We combine:
  1. Curated SMARTS structural alerts (Brenk, PAINS-style families).
  2. Lipinski/physchem flags from RDKit descriptors.
  3. A weighted sum -> score in [0, 1] -> {low, moderate, high} band.

The LLM consumes this output to write rationale; it does not invent the score.
See ARCHITECTURE.md for the honest scope statement.
"""
from __future__ import annotations

from typing import Any

from rdkit import Chem

from app.services.rdkit_tools import _mol, descriptors

# A small, curated alert list. Enough to demo on common compounds without
# shipping a 500-line SMARTS table. Each entry: (name, smarts, severity, why).
ALERTS: list[tuple[str, str, str, str]] = [
    (
        "Aromatic nitro",
        "[NX3](=O)=O",
        "high",
        "Aromatic nitro groups associated with mutagenicity (Ames+) in many series.",
    ),
    (
        "Aromatic amine",
        "c[NH2]",
        "medium",
        "Primary aromatic amines can form reactive nitrenium ions (CYP-mediated).",
    ),
    (
        "Aldehyde",
        "[CX3H1](=O)[#6]",
        "medium",
        "Aldehydes are electrophilic and can form protein adducts.",
    ),
    (
        "Epoxide",
        "C1OC1",
        "high",
        "Epoxides are reactive electrophiles, common DNA-damage liability.",
    ),
    (
        "Michael acceptor (acrylamide)",
        "C=CC(=O)N",
        "high",
        "α,β-unsaturated carbonyls react with cysteine/glutathione thiols.",
    ),
    (
        "Hydrazine",
        "[NX3][NX3]",
        "high",
        "Hydrazines are strongly associated with hepatotoxicity and mutagenicity.",
    ),
    (
        "Polyhalogenated aromatic",
        "c(Cl)c(Cl)c(Cl)",
        "medium",
        "Polychlorinated aromatics correlate with persistence/AhR activation.",
    ),
    (
        "Quinone",
        "O=C1C=CC(=O)C=C1",
        "medium",
        "Quinones redox cycle, generating ROS and reactive Michael acceptors.",
    ),
    (
        "Thiol",
        "[#6][SX2H]",
        "low",
        "Free thiols can be reactive but are common in biology; weak alert.",
    ),
    (
        "Acyl halide",
        "[CX3](=O)[F,Cl,Br,I]",
        "high",
        "Highly reactive electrophile.",
    ),
]

_SEV_WEIGHT = {"low": 0.05, "medium": 0.15, "high": 0.30}
_PHYSCHEM_WEIGHT = 0.05  # per flag


def find_alerts(smiles: str) -> list[dict[str, Any]]:
    mol = _mol(smiles)
    hits: list[dict[str, Any]] = []
    for name, smarts, severity, why in ALERTS:
        pat = Chem.MolFromSmarts(smarts)
        if pat is None:
            continue
        if mol.HasSubstructMatch(pat):
            hits.append(
                {
                    "name": name,
                    "smarts": smarts,
                    "severity": severity,
                    "description": why,
                }
            )
    return hits


def physchem_flags(desc: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if (mw := desc.get("mw")) is not None and mw > 500:
        flags.append(f"MW > 500 ({mw:.0f})")
    if (logp := desc.get("logp")) is not None and logp > 5:
        flags.append(f"logP > 5 ({logp:.2f}) — potential bioaccumulation")
    if (logp := desc.get("logp")) is not None and logp < -2:
        flags.append(f"logP < -2 ({logp:.2f}) — poor permeability")
    if (tpsa := desc.get("tpsa")) is not None and tpsa > 140:
        flags.append(f"TPSA > 140 ({tpsa:.0f}) — likely poor oral absorption")
    if desc.get("lipinski_violations", 0) >= 2:
        flags.append(f"{desc['lipinski_violations']} Lipinski violations")
    if (qed := desc.get("qed")) is not None and qed < 0.3:
        flags.append(f"Low QED ({qed:.2f}) — drug-likeness concern")
    return flags


def score(smiles: str) -> dict[str, Any]:
    """Return {score, risk_band, confidence, structural_alerts, physchem_flags}."""
    desc = descriptors(smiles)
    alerts = find_alerts(smiles)
    flags = physchem_flags(desc)

    raw = sum(_SEV_WEIGHT[a["severity"]] for a in alerts) + _PHYSCHEM_WEIGHT * len(flags)
    s = min(1.0, raw)

    if s < 0.2:
        band = "low"
    elif s < 0.5:
        band = "moderate"
    else:
        band = "high"

    # Confidence reflects evidence volume, not correctness. More signals = more
    # confident in the band assignment, capped at 0.85 because this is not an
    # ML model.
    confidence = min(0.85, 0.4 + 0.07 * (len(alerts) + len(flags)))

    return {
        "score": round(s, 3),
        "risk_band": band,
        "confidence": round(confidence, 3),
        "structural_alerts": alerts,
        "physchem_flags": flags,
    }

"""Smoke tests for the toxicity heuristic."""
import pytest

from app.services import toxicity


def test_caffeine_low_risk():
    s = toxicity.score("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")
    assert s["risk_band"] == "low"
    assert s["score"] < 0.2


def test_acrolein_high_risk():
    # Aldehyde + Michael acceptor — should land moderate or high.
    s = toxicity.score("C=CC=O")
    assert s["risk_band"] in ("moderate", "high")
    assert any(a["name"] == "Aldehyde" for a in s["structural_alerts"])


def test_invalid_smiles_raises():
    with pytest.raises(Exception):
        toxicity.score("not-a-smiles")

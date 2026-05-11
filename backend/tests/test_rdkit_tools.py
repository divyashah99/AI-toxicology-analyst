from app.services import rdkit_tools


def test_descriptors_caffeine():
    d = rdkit_tools.descriptors("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")
    assert 190 < d["mw"] < 200
    assert d["aromatic_rings"] >= 1
    assert d["lipinski_violations"] == 0


def test_canonicalize_round_trip():
    s1 = rdkit_tools.canonical_smiles("c1ccccc1O")
    s2 = rdkit_tools.canonical_smiles(s1)
    assert s1 == s2


def test_tanimoto_self_is_one():
    assert rdkit_tools.tanimoto("CCO", "CCO") == 1.0

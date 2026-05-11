"""RDKit-backed cheminformatics. Pure compute, no I/O."""
from __future__ import annotations

from typing import Any

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Crippen, Descriptors, Lipinski, QED, rdMolDescriptors
from rdkit.DataStructs import TanimotoSimilarity

# RDKit prints to stderr on parse failures; silence the noisy ones.
RDLogger.DisableLog("rdApp.warning")


class RDKitError(ValueError):
    pass


def _mol(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise RDKitError(f"Invalid SMILES: {smiles!r}")
    return mol


def descriptors(smiles: str) -> dict[str, Any]:
    mol = _mol(smiles)
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    rb = Lipinski.NumRotatableBonds(mol)
    arom = rdMolDescriptors.CalcNumAromaticRings(mol)
    heavy = mol.GetNumHeavyAtoms()
    qed = QED.qed(mol)

    violations = sum(
        [
            mw > 500,
            logp > 5,
            hbd > 5,
            hba > 10,
        ]
    )

    return {
        "mw": round(mw, 3),
        "logp": round(logp, 3),
        "tpsa": round(tpsa, 3),
        "h_donors": hbd,
        "h_acceptors": hba,
        "rotatable_bonds": rb,
        "aromatic_rings": arom,
        "heavy_atoms": heavy,
        "qed": round(qed, 3),
        "lipinski_violations": violations,
    }


def morgan_fingerprint(smiles: str, radius: int = 2, n_bits: int = 2048) -> list[int]:
    mol = _mol(smiles)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=radius, nBits=n_bits)
    return list(fp)


def tanimoto(smiles_a: str, smiles_b: str, radius: int = 2, n_bits: int = 2048) -> float:
    mol_a = _mol(smiles_a)
    mol_b = _mol(smiles_b)
    fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, radius, n_bits)
    fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, radius, n_bits)
    return float(TanimotoSimilarity(fp_a, fp_b))


def canonical_smiles(smiles: str) -> str:
    return Chem.MolToSmiles(_mol(smiles))


def inchi_keys(smiles: str) -> dict[str, str]:
    mol = _mol(smiles)
    return {
        "inchi": Chem.MolToInchi(mol),
        "inchikey": Chem.MolToInchiKey(mol),
    }

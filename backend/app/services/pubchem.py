"""PubChem PUG REST client. Free, no API key required.

Docs: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger

log = get_logger("services.pubchem")

_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
# PubChem renamed CanonicalSMILES -> SMILES and IsomericSMILES -> (gone) /
# ConnectivitySMILES around 2025. Request the new names; older deployments
# that still serve the legacy fields are handled in the consumer.
_PROPERTIES = (
    "MolecularFormula,MolecularWeight,SMILES,ConnectivitySMILES,"
    "InChI,InChIKey,IUPACName,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,"
    "RotatableBondCount,HeavyAtomCount"
)

_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.4, min=0.4, max=4),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
)


class PubChemError(RuntimeError):
    pass


class PubChemClient:
    def __init__(self, timeout: float = 15.0) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "ai-toxicology-analyst/0.1"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @_retry
    async def _get(self, path: str) -> dict[str, Any]:
        r = await self._client.get(f"{_BASE}{path}")
        if r.status_code == 404:
            raise PubChemError(f"Not found: {path}")
        r.raise_for_status()
        return r.json()

    async def cid_by_name(self, name: str) -> int | None:
        try:
            data = await self._get(f"/compound/name/{quote(name, safe='')}/cids/JSON")
        except PubChemError:
            return None
        cids = data.get("IdentifierList", {}).get("CID", [])
        return cids[0] if cids else None

    async def cid_by_smiles(self, smiles: str) -> int | None:
        # SMILES contains characters that confuse URL parsers. POST is the
        # canonical PUG REST pattern for arbitrary SMILES.
        try:
            r = await self._client.post(
                f"{_BASE}/compound/smiles/cids/JSON",
                data={"smiles": smiles},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
        except (httpx.TransportError, httpx.HTTPStatusError):
            return None
        cids = data.get("IdentifierList", {}).get("CID", [])
        return cids[0] if cids else None

    async def properties(self, cid: int) -> dict[str, Any]:
        data = await self._get(f"/compound/cid/{cid}/property/{_PROPERTIES}/JSON")
        rows = data.get("PropertyTable", {}).get("Properties", [])
        return rows[0] if rows else {}

    async def synonyms(self, cid: int, limit: int = 5) -> list[str]:
        try:
            data = await self._get(f"/compound/cid/{cid}/synonyms/JSON")
        except PubChemError:
            return []
        names = data.get("InformationList", {}).get("Information", [{}])[0].get(
            "Synonym", []
        )
        return names[:limit]


_client_singleton: PubChemClient | None = None


def get_pubchem() -> PubChemClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = PubChemClient()
    return _client_singleton

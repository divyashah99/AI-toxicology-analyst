"""MCP server: PubChem identity + metadata.

Implemented with the real `mcp.server.Server`. Connects to the client via
in-memory streams (see `mcp_client.client`). Same tool surface as before.
"""
from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from app.mcp_servers.base import ServerModule, text_result
from app.services.pubchem import get_pubchem

_server = Server("pubchem")

_TOOLS = [
    Tool(
        name="search_compound",
        description=(
            "Resolve a compound to a PubChem CID by name or SMILES. "
            "Returns {cid} or {cid: null}."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "smiles": {"type": "string"},
            },
            "anyOf": [{"required": ["name"]}, {"required": ["smiles"]}],
        },
    ),
    Tool(
        name="get_properties",
        description=(
            "Fetch canonical properties for a CID "
            "(formula, MW, SMILES, InChI, IUPAC, logP)."
        ),
        inputSchema={
            "type": "object",
            "properties": {"cid": {"type": "integer"}},
            "required": ["cid"],
        },
    ),
    Tool(
        name="get_synonyms",
        description="Return up to N synonyms / common names for a CID.",
        inputSchema={
            "type": "object",
            "properties": {
                "cid": {"type": "integer"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["cid"],
        },
    ),
]


@_server.list_tools()
async def _list_tools() -> list[Tool]:
    return _TOOLS


@_server.call_tool()
async def _call_tool(name: str, arguments: dict):
    pc = get_pubchem()
    if name == "search_compound":
        cid = None
        if arguments.get("name"):
            cid = await pc.cid_by_name(arguments["name"])
        if cid is None and arguments.get("smiles"):
            cid = await pc.cid_by_smiles(arguments["smiles"])
        return text_result({"cid": cid})

    if name == "get_properties":
        props = await pc.properties(int(arguments["cid"]))
        smiles = (
            props.get("SMILES")
            or props.get("IsomericSMILES")
            or props.get("CanonicalSMILES")
            or props.get("ConnectivitySMILES")
        )
        return text_result(
            {
                "cid": props.get("CID"),
                "iupac_name": props.get("IUPACName"),
                "smiles": smiles,
                "inchi": props.get("InChI"),
                "inchikey": props.get("InChIKey"),
                "formula": props.get("MolecularFormula"),
                "mw": float(props["MolecularWeight"])
                if props.get("MolecularWeight")
                else None,
                "xlogp": props.get("XLogP"),
                "tpsa": props.get("TPSA"),
            }
        )

    if name == "get_synonyms":
        names = await pc.synonyms(
            int(arguments["cid"]), int(arguments.get("limit", 5))
        )
        return text_result({"synonyms": names})

    raise ValueError(f"Unknown tool: pubchem.{name}")


module = ServerModule(
    name="pubchem",
    description="PubChem identity, properties, and synonyms via PUG REST.",
    server=_server,
)

"""MCP server: RDKit cheminformatics."""
from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from app.mcp_servers.base import ServerModule, text_result
from app.services import rdkit_tools

_server = Server("rdkit")

_TOOLS = [
    Tool(
        name="descriptors",
        description=(
            "Compute MW, logP, TPSA, H-bond donors/acceptors, rotatable bonds, "
            "aromatic rings, heavy atoms, QED, and Lipinski violations from SMILES."
        ),
        inputSchema={
            "type": "object",
            "properties": {"smiles": {"type": "string"}},
            "required": ["smiles"],
        },
    ),
    Tool(
        name="canonicalize",
        description="Return canonical SMILES + InChI + InChIKey for a SMILES.",
        inputSchema={
            "type": "object",
            "properties": {"smiles": {"type": "string"}},
            "required": ["smiles"],
        },
    ),
    Tool(
        name="fingerprint",
        description="Morgan (ECFP) bit fingerprint for a SMILES.",
        inputSchema={
            "type": "object",
            "properties": {
                "smiles": {"type": "string"},
                "radius": {"type": "integer", "default": 2},
                "n_bits": {"type": "integer", "default": 2048},
            },
            "required": ["smiles"],
        },
    ),
    Tool(
        name="similarity",
        description="Tanimoto similarity between two SMILES via Morgan fingerprints.",
        inputSchema={
            "type": "object",
            "properties": {
                "smiles_a": {"type": "string"},
                "smiles_b": {"type": "string"},
            },
            "required": ["smiles_a", "smiles_b"],
        },
    ),
]


@_server.list_tools()
async def _list_tools() -> list[Tool]:
    return _TOOLS


@_server.call_tool()
async def _call_tool(name: str, arguments: dict):
    if name == "descriptors":
        return text_result(rdkit_tools.descriptors(arguments["smiles"]))

    if name == "canonicalize":
        smi = rdkit_tools.canonical_smiles(arguments["smiles"])
        keys = rdkit_tools.inchi_keys(smi)
        return text_result({"canonical_smiles": smi, **keys})

    if name == "fingerprint":
        bits = rdkit_tools.morgan_fingerprint(
            arguments["smiles"],
            int(arguments.get("radius", 2)),
            int(arguments.get("n_bits", 2048)),
        )
        return text_result({"n_bits": len(bits), "on_bits": sum(bits)})

    if name == "similarity":
        return text_result(
            {
                "tanimoto": rdkit_tools.tanimoto(
                    arguments["smiles_a"], arguments["smiles_b"]
                )
            }
        )

    raise ValueError(f"Unknown tool: rdkit.{name}")


module = ServerModule(
    name="rdkit",
    description="RDKit-backed descriptors, fingerprints, and similarity.",
    server=_server,
)

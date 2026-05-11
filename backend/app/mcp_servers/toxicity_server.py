"""MCP server: heuristic toxicity scoring."""
from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from app.mcp_servers.base import ServerModule, text_result
from app.services import toxicity

_server = Server("toxicity")

_TOOLS = [
    Tool(
        name="score",
        description=(
            "Compute risk score in [0,1], risk band, confidence, structural "
            "alerts (with SMARTS + severity), and physchem flags from SMILES."
        ),
        inputSchema={
            "type": "object",
            "properties": {"smiles": {"type": "string"}},
            "required": ["smiles"],
        },
    ),
    Tool(
        name="alerts",
        description="Return only structural alert hits for a SMILES.",
        inputSchema={
            "type": "object",
            "properties": {"smiles": {"type": "string"}},
            "required": ["smiles"],
        },
    ),
    Tool(
        name="classify",
        description=(
            "Map a numeric score in [0,1] to a risk band: low (<0.2), "
            "moderate (<0.5), high (>=0.5)."
        ),
        inputSchema={
            "type": "object",
            "properties": {"score": {"type": "number"}},
            "required": ["score"],
        },
    ),
]


@_server.list_tools()
async def _list_tools() -> list[Tool]:
    return _TOOLS


@_server.call_tool()
async def _call_tool(name: str, arguments: dict):
    if name == "score":
        return text_result(toxicity.score(arguments["smiles"]))

    if name == "alerts":
        return text_result({"alerts": toxicity.find_alerts(arguments["smiles"])})

    if name == "classify":
        s = float(arguments["score"])
        band = "low" if s < 0.2 else "moderate" if s < 0.5 else "high"
        return text_result({"risk_band": band})

    raise ValueError(f"Unknown tool: toxicity.{name}")


module = ServerModule(
    name="toxicity",
    description=(
        "Heuristic toxicity assessment: structural alerts + physchem flags. "
        "Not a trained ML model — see ARCHITECTURE.md."
    ),
    server=_server,
)

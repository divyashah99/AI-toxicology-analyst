"""MCP server: research paper ingestion + retrieval."""
from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from app.mcp_servers.base import ServerModule, text_result
from app.services import chroma, papers

_server = Server("papers")

_TOOLS = [
    Tool(
        name="retrieve",
        description=(
            "Semantic search over previously ingested papers. Optionally restrict "
            "to a list of paper_ids. Returns top-k chunks with page numbers."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "paper_ids": {"type": "array", "items": {"type": "string"}},
                "k": {"type": "integer", "default": 6},
            },
            "required": ["question"],
        },
    ),
    Tool(
        name="library_stats",
        description="Return total chunk count across all ingested papers.",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@_server.list_tools()
async def _list_tools() -> list[Tool]:
    return _TOOLS


@_server.call_tool()
async def _call_tool(name: str, arguments: dict):
    if name == "retrieve":
        chunks = await papers.retrieve(
            arguments["question"],
            paper_ids=arguments.get("paper_ids") or None,
            k=int(arguments.get("k", 6)),
        )
        return text_result(
            {
                "chunks": [
                    {
                        "paper_id": c["metadata"]["paper_id"],
                        "chunk_idx": c["metadata"]["chunk_idx"],
                        "page": c["metadata"]["page"],
                        "text": c["text"],
                        "score": round(c["score"], 4),
                    }
                    for c in chunks
                ]
            }
        )

    if name == "library_stats":
        return text_result({"chunks_indexed": chroma.count()})

    raise ValueError(f"Unknown tool: papers.{name}")


module = ServerModule(
    name="papers",
    description="PDF parse, embed, and semantic retrieval over uploaded papers.",
    server=_server,
)

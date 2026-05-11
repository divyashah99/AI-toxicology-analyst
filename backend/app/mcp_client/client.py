"""Real MCP client.

Connects to each in-process `mcp.server.Server` via in-memory JSON-RPC streams
(`create_connected_server_and_client_session`), then exposes a single
`call(server, tool, args)` entry point that the agent uses. Every call emits
structured trace events so the UI can render the reasoning timeline.

Exit ramp to subprocess MCP: swap `create_connected_server_and_client_session`
for `stdio_client(...)` with a spawned `python -m app.mcp_servers.<name>`. The
server modules themselves are already real MCP and need no changes.
"""
from __future__ import annotations

import json
import time
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable

from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult, TextContent

from app.core.logging import get_logger
from app.mcp_servers.papers_server import module as papers_module
from app.mcp_servers.pubchem_server import module as pubchem_module
from app.mcp_servers.rdkit_server import module as rdkit_module
from app.mcp_servers.toxicity_server import module as toxicity_module
from app.models.schemas import TraceEvent

log = get_logger("mcp.client")

TraceSink = Callable[[TraceEvent], Awaitable[None]]


class McpClient:
    """Holds one ClientSession per server module."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, ClientSession] = {}
        self._tool_cache: dict[str, list[dict[str, Any]]] = {}
        self._modules = (
            pubchem_module,
            rdkit_module,
            papers_module,
            toxicity_module,
        )

    async def start(self) -> None:
        """Spin up each server in an anyio task group and connect a client."""
        self._stack = AsyncExitStack()
        for mod in self._modules:
            session = await self._stack.enter_async_context(
                create_connected_server_and_client_session(
                    mod.server, raise_exceptions=True
                )
            )
            self._sessions[mod.name] = session
            tools = await session.list_tools()
            self._tool_cache[mod.name] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tools.tools
            ]
        log.info(
            "mcp.start",
            servers=list(self._sessions),
            tool_counts={k: len(v) for k, v in self._tool_cache.items()},
        )

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._sessions.clear()
        # Close shared httpx client for PubChem (owned by the service module).
        from app.services.pubchem import _client_singleton  # noqa: PLC0415

        if _client_singleton is not None:
            await _client_singleton.aclose()
        log.info("mcp.stop")

    # ----- discovery -----

    def list_servers(self) -> list[dict[str, Any]]:
        return [
            {
                "name": mod.name,
                "description": mod.description,
                "tools": self._tool_cache.get(mod.name, []),
            }
            for mod in self._modules
        ]

    def tool_catalog(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for mod in self._modules:
            for t in self._tool_cache.get(mod.name, []):
                out.append(
                    {
                        "server": mod.name,
                        "tool": t["name"],
                        "qualified_name": f"{mod.name}.{t['name']}",
                        "description": t["description"],
                        "input_schema": t["input_schema"],
                    }
                )
        return out

    # ----- dispatch -----

    async def call(
        self,
        server: str,
        tool: str,
        args: dict[str, Any] | None = None,
        *,
        trace: TraceSink | None = None,
    ) -> Any:
        session = self._sessions.get(server)
        if session is None:
            raise KeyError(f"Unknown MCP server: {server}")
        args = args or {}

        if trace:
            await trace(
                TraceEvent(
                    kind="tool_call",
                    label=f"{server}.{tool}",
                    server=server,
                    tool=tool,
                    args=args,
                )
            )

        t0 = time.perf_counter()
        try:
            result: CallToolResult = await session.call_tool(tool, args)
        except Exception as exc:
            if trace:
                await trace(
                    TraceEvent(
                        kind="error",
                        label=f"{server}.{tool} failed",
                        server=server,
                        tool=tool,
                        text=str(exc),
                    )
                )
            raise

        dt = int((time.perf_counter() - t0) * 1000)
        payload = _unwrap(result)

        if trace:
            await trace(
                TraceEvent(
                    kind="tool_result",
                    label=f"{server}.{tool}",
                    server=server,
                    tool=tool,
                    output=_truncate(payload),
                    duration_ms=dt,
                )
            )

        if isinstance(result, CallToolResult) and result.isError:
            # Surface tool errors as exceptions so the agent's try/except path runs.
            raise RuntimeError(f"{server}.{tool} reported error: {payload}")

        return payload


def _unwrap(result: CallToolResult) -> Any:
    """Decode `[TextContent(json)]` back into the original Python object.

    All our servers wrap a single JSON TextContent. Be defensive: if the server
    returns multiple content blocks or non-text content, return a structured
    fallback rather than crashing.
    """
    if not result.content:
        return None
    if len(result.content) == 1 and isinstance(result.content[0], TextContent):
        try:
            return json.loads(result.content[0].text)
        except json.JSONDecodeError:
            return {"text": result.content[0].text}
    return {
        "blocks": [
            {"type": getattr(b, "type", "unknown"), "text": getattr(b, "text", None)}
            for b in result.content
        ]
    }


def _truncate(obj: Any, max_chars: int = 2000) -> Any:
    """Trim large outputs in trace events so the UI stays snappy."""
    s = json.dumps(obj, default=str)
    if len(s) <= max_chars:
        return obj
    return {"_truncated": True, "preview": s[:max_chars]}

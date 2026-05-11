"""Thin container that pairs a real `mcp.server.Server` with display metadata.

We keep one of these per domain (pubchem, rdkit, papers, toxicity). Each module
constructs its own `Server`, registers handlers via the SDK's
`@server.list_tools()` / `@server.call_tool()` decorators, and exposes the
result as a `ServerModule`. The client iterates these and connects to each via
in-memory JSON-RPC streams.

Splitting them into separate processes later is mechanical: replace
`create_connected_server_and_client_session` with `stdio_client(...)` in the
client; the server modules themselves don't change.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mcp.server import Server
from mcp.types import TextContent


@dataclass
class ServerModule:
    name: str
    description: str
    server: Server


def text_result(payload: Any) -> list[TextContent]:
    """Standard wrapper: serialize a JSON-friendly object as a TextContent block.

    MCP tools can return mixed content (text, images, embedded resources). For
    our purely-data tools, one JSON TextContent is the cleanest contract.
    """
    return [TextContent(type="text", text=json.dumps(payload, default=str))]

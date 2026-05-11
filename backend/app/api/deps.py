"""FastAPI dependency providers."""
from __future__ import annotations

from fastapi import Request

from app.mcp_client.client import McpClient


def get_mcp(request: Request) -> McpClient:
    return request.app.state.mcp

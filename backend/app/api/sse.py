"""SSE helpers for streaming trace + LLM tokens to the browser."""
from __future__ import annotations

import json
from typing import AsyncIterator

from app.models.schemas import TraceEvent


def sse_format(event: str, data: dict | str) -> bytes:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode()


async def trace_to_sse(
    events: AsyncIterator[TraceEvent],
) -> AsyncIterator[bytes]:
    async for ev in events:
        yield sse_format(ev.kind, ev.model_dump(mode="json"))
    yield sse_format("end", {"ok": True})

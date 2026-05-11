"""Trace helpers: an asyncio.Queue-based event bus for streaming to SSE."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from app.models.schemas import TraceEvent


class TraceBus:
    def __init__(self) -> None:
        self._q: asyncio.Queue[TraceEvent | None] = asyncio.Queue()
        self.events: list[TraceEvent] = []

    async def emit(self, ev: TraceEvent) -> None:
        self.events.append(ev)
        await self._q.put(ev)

    async def close(self) -> None:
        await self._q.put(None)

    async def stream(self) -> AsyncIterator[TraceEvent]:
        while True:
            ev = await self._q.get()
            if ev is None:
                return
            yield ev

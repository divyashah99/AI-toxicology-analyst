"""Embeddings via OpenAI. Batches calls; retries on transient errors."""
from __future__ import annotations

from typing import Iterable

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

_settings = get_settings()
_client: AsyncOpenAI | None = None


def _get() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not _settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY required for embeddings")
        _client = AsyncOpenAI(api_key=_settings.openai_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
async def embed_texts(texts: Iterable[str], batch_size: int = 64) -> list[list[float]]:
    """Return embeddings preserving input order."""
    items = list(texts)
    out: list[list[float]] = []
    client = _get()
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        resp = await client.embeddings.create(
            model=_settings.openai_embed_model, input=batch
        )
        out.extend([d.embedding for d in resp.data])
    return out


async def embed_one(text: str) -> list[float]:
    return (await embed_texts([text]))[0]

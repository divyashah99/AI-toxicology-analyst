"""Thin LLM wrapper. OpenAI by default; Groq when LLM_PROVIDER=groq.

We expose two operations:
  - chat(messages, response_format=None) -> string or parsed dict
  - stream(messages) -> async iterator of content deltas

Both providers expose OpenAI-compatible chat APIs, so we share one code path.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from app.config import get_settings


_settings = get_settings()
_client: AsyncOpenAI | None = None


def _get_client() -> tuple[AsyncOpenAI, str]:
    global _client
    if _client is None:
        if _settings.llm_provider == "groq":
            if not _settings.groq_api_key:
                raise RuntimeError("GROQ_API_KEY required when LLM_PROVIDER=groq")
            _client = AsyncOpenAI(
                api_key=_settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            return _client, _settings.groq_model
        if not _settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY required")
        _client = AsyncOpenAI(api_key=_settings.openai_api_key)
    model = (
        _settings.groq_model
        if _settings.llm_provider == "groq"
        else _settings.openai_model
    )
    return _client, model


async def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    response_format: dict[str, Any] | None = None,
) -> str:
    client, model = _get_client()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


async def stream(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> AsyncIterator[str]:
    client, model = _get_client()
    s = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in s:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content

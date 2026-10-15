"""OpenAI-compatible streaming for NIM / OpenAI / OpenRouter (no new deps)."""
from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from ..config import get_settings


def _client_for(provider: str) -> AsyncOpenAI:
    s = get_settings()
    if provider == "nim":
        if not s.nim_api_key:
            raise PermissionError("nim: missing API key — add an NVIDIA NIM key in Settings.")
        return AsyncOpenAI(base_url=s.nim_base_url, api_key=s.nim_api_key, timeout=120.0, max_retries=1)
    if provider == "openai":
        if not s.openai_api_key:
            raise PermissionError("openai: missing API key — add it in Settings.")
        return AsyncOpenAI(base_url=s.openai_base_url, api_key=s.openai_api_key, timeout=120.0, max_retries=1)
    if provider == "openrouter":
        if not s.openrouter_api_key:
            raise PermissionError("openrouter: missing API key — add it in Settings.")
        return AsyncOpenAI(base_url=s.openrouter_base_url, api_key=s.openrouter_api_key, timeout=120.0, max_retries=1)
    raise ValueError(f"unknown OpenAI-compat provider '{provider}'")


async def stream_openai_compat(
    provider: str, model: str, system: str, user: str, max_tokens: int = 4096
) -> AsyncIterator[tuple[str, str]]:
    client = _client_for(provider)
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        try:
            delta = chunk.choices[0].delta
            content = delta.content or ""
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None) or ""
        except Exception:
            continue
        if content:
            yield ("content", content)
        if reasoning:
            yield ("reasoning", reasoning if isinstance(reasoning, str) else str(reasoning))

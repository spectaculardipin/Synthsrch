"""Anthropic native streaming via httpx (no extra SDK)."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from ..config import get_settings


async def stream_anthropic(
    model: str, system: str, user: str, max_tokens: int = 4096
) -> AsyncIterator[tuple[str, str]]:
    s = get_settings()
    if not s.anthropic_api_key:
        raise PermissionError("anthropic: missing API key — add it in Settings.")
    payload = {
        "model": model,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {
        "x-api-key": s.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120.0) as c:
        async with c.stream("POST", "https://api.anthropic.com/v1/messages", json=payload, headers=headers) as r:
            if r.status_code in (401, 402, 429):
                raise RuntimeError(f"anthropic: provider error {r.status_code} — check key/credits.")
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data in ("[DONE]", ""):
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                t = obj.get("type", "")
                if t == "content_block_delta":
                    delta = obj.get("delta", {})
                    if delta.get("type") == "thinking_delta":
                        yield ("reasoning", delta.get("thinking", ""))
                    elif "text" in delta:
                        yield ("content", delta.get("text", ""))
                elif t == "message_delta" and "text" in obj.get("delta", {}):
                    yield ("content", obj["delta"]["text"])

"""Gemini native streaming via httpx (no extra SDK)."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from urllib.parse import quote

import httpx

from ..config import get_settings


async def stream_gemini(
    model: str, system: str, user: str, max_tokens: int = 4096
) -> AsyncIterator[tuple[str, str]]:
    s = get_settings()
    if not s.gemini_api_key:
        raise PermissionError("gemini: missing API key — add it in Settings.")
    mid = quote(model, safe="/-_.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mid}:streamGenerateContent?alt=sse&key={s.gemini_api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    async with httpx.AsyncClient(timeout=120.0) as c:
        async with c.stream("POST", url, json=payload) as r:
            if r.status_code in (400, 401, 402, 429):
                body = (await r.aread())[:300].decode(errors="ignore")
                raise RuntimeError(f"gemini: provider error {r.status_code} — {body}")
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
                for cand in obj.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("text"):
                            # Thinking traces (thought:true) belong in the
                            # Thinking box, never in the answer body.
                            yield ("reasoning" if part.get("thought") else "content", part["text"])

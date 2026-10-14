"""Serper search adapter — SEARCH ONLY."""
from __future__ import annotations

import httpx

from ..config import get_settings
from .base import SearchRequest, SearchResult, publisher_of, result_id


class SerperAdapter:
    name = "serper"

    async def search(self, req: SearchRequest, client: httpx.AsyncClient | None = None) -> list[SearchResult]:
        key = get_settings().serper_api_key
        if not key:
            raise PermissionError("serper: missing API key — add it in Settings.")
        need = max(req.effective_end(), req.count)
        fetch_n = min(100, max(need, 10))
        payload = {"q": req.query, "num": fetch_n}
        own = client is None
        c = client or httpx.AsyncClient(timeout=get_settings().search_timeout_s)
        try:
            r = await c.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code in (401, 402, 429):
                raise RuntimeError(f"serper: provider error {r.status_code} — check key/credits.")
            r.raise_for_status()
            data = r.json()
        finally:
            if own:
                await c.aclose()
        out: list[SearchResult] = []
        for i, item in enumerate(data.get("organic", []), start=1):
            url = str(item.get("link", ""))
            if not url:
                continue
            out.append(
                SearchResult(
                    id=result_id("serper", url),
                    title=str(item.get("title", ""))[:300],
                    url=url,
                    publisher=publisher_of(url),
                    rank=i,
                    score=None,
                    snippet=str(item.get("snippet", ""))[:600],
                )
            )
        return out

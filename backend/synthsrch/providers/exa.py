"""Exa search adapter — SEARCH ONLY (never /contents)."""
from __future__ import annotations

import httpx

from ..config import get_settings
from .base import SearchRequest, SearchResult, publisher_of, result_id


class ExaAdapter:
    name = "exa"

    async def search(self, req: SearchRequest, client: httpx.AsyncClient | None = None) -> list[SearchResult]:
        key = get_settings().exa_api_key
        if not key:
            raise PermissionError("exa: missing API key — add it in Settings.")
        need = max(req.effective_end(), req.count)
        fetch_n = min(100, max(need, 5))
        # search-only: no contents.text/highlights (that bills extract). Snippet from autotitle.
        payload = {"query": req.query, "type": "auto", "numResults": fetch_n}
        own = client is None
        c = client or httpx.AsyncClient(timeout=get_settings().search_timeout_s)
        try:
            r = await c.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": key, "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code in (401, 402, 429):
                raise RuntimeError(f"exa: provider error {r.status_code} — check key/credits.")
            r.raise_for_status()
            data = r.json()
        finally:
            if own:
                await c.aclose()
        out: list[SearchResult] = []
        for i, item in enumerate(data.get("results", []), start=1):
            url = str(item.get("url", ""))
            if not url:
                continue
            out.append(
                SearchResult(
                    id=result_id("exa", url),
                    title=str(item.get("title", ""))[:300],
                    url=url,
                    publisher=publisher_of(url),
                    rank=i,
                    score=float(item["score"]) if item.get("score") is not None else None,
                    snippet=str(item.get("text", "") or item.get("title", ""))[:600],
                )
            )
        return out

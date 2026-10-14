"""Tavily search adapter — SEARCH ONLY (never include_raw_content/extract)."""
from __future__ import annotations

import httpx

from ..config import get_settings
from .base import SearchRequest, SearchResult, publisher_of, result_id


class TavilyAdapter:
    name = "tavily"

    async def search(self, req: SearchRequest, client: httpx.AsyncClient | None = None) -> list[SearchResult]:
        key = get_settings().tavily_api_key
        if not key:
            raise PermissionError("tavily: missing API key — add it in Settings.")
        # Tavily caps max_results at 20; fetch max needed for rank window.
        need = max(req.effective_end(), req.count)
        fetch_n = min(20, max(need, 5))
        payload = {
            "query": req.query,
            "search_depth": "basic",
            "max_results": fetch_n,
            "include_answer": False,
            "include_raw_content": False,  # search-only rule
            "include_images": False,
        }
        own = client is None
        c = client or httpx.AsyncClient(timeout=get_settings().search_timeout_s)
        try:
            r = await c.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code in (401, 402, 429):
                raise RuntimeError(f"tavily: provider error {r.status_code} — check key/credits.")
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
                    id=result_id("tavily", url),
                    title=str(item.get("title", ""))[:300],
                    url=url,
                    publisher=publisher_of(url),
                    rank=i,
                    score=float(item["score"]) if item.get("score") is not None else None,
                    snippet=str(item.get("content", ""))[:600],
                )
            )
        return out

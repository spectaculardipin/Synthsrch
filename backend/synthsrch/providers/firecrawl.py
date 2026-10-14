"""Firecrawl search adapter — SEARCH ONLY (never scrapeOptions)."""
from __future__ import annotations

import httpx

from ..config import get_settings
from .base import SearchRequest, SearchResult, publisher_of, result_id


class FirecrawlAdapter:
    name = "firecrawl"

    async def search(self, req: SearchRequest, client: httpx.AsyncClient | None = None) -> list[SearchResult]:
        key = get_settings().firecrawl_api_key
        if not key:
            raise PermissionError("firecrawl: missing API key — add it in Settings.")
        need = max(req.effective_end(), req.count)
        fetch_n = min(100, max(need, 5))
        # search-only: no scrapeOptions (that triggers crawl billing)
        payload = {"query": req.query, "limit": fetch_n, "sources": ["web"]}
        own = client is None
        c = client or httpx.AsyncClient(timeout=get_settings().search_timeout_s)
        try:
            r = await c.post(
                "https://api.firecrawl.dev/v2/search",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code in (401, 402, 429):
                raise RuntimeError(f"firecrawl: provider error {r.status_code} — check key/credits.")
            r.raise_for_status()
            data = r.json()
        finally:
            if own:
                await c.aclose()
        items = data.get("data", {}).get("web", []) if isinstance(data.get("data"), dict) else data.get("data", [])
        if isinstance(items, dict):
            items = items.get("web", [])
        out: list[SearchResult] = []
        for i, item in enumerate(items or [], start=1):
            url = str(item.get("url", ""))
            if not url:
                continue
            out.append(
                SearchResult(
                    id=result_id("firecrawl", url),
                    title=str(item.get("title", ""))[:300],
                    url=url,
                    publisher=publisher_of(url),
                    rank=i,
                    score=None,
                    snippet=str(item.get("description", "") or item.get("markdown", ""))[:600],
                )
            )
        return out

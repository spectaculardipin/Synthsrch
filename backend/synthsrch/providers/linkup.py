"""Linkup search adapter — SEARCH ONLY (outputType searchResults, no fetch)."""
from __future__ import annotations

import httpx

from ..config import get_settings
from .base import SearchRequest, SearchResult, publisher_of, result_id


class LinkupAdapter:
    name = "linkup"

    async def search(self, req: SearchRequest, client: httpx.AsyncClient | None = None) -> list[SearchResult]:
        key = get_settings().linkup_api_key
        if not key:
            raise PermissionError("linkup: missing API key — add it in Settings.")
        payload = {"q": req.query, "depth": "standard", "outputType": "searchResults"}
        own = client is None
        c = client or httpx.AsyncClient(timeout=get_settings().search_timeout_s)
        try:
            r = await c.post(
                "https://api.linkup.so/v1/search",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code in (401, 402, 429):
                raise RuntimeError(f"linkup: provider error {r.status_code} — check key/credits.")
            r.raise_for_status()
            data = r.json()
        finally:
            if own:
                await c.aclose()
        items = data.get("results") or data.get("sources") or []
        out: list[SearchResult] = []
        for i, item in enumerate(items, start=1):
            url = str(item.get("url", ""))
            if not url:
                continue
            out.append(
                SearchResult(
                    id=result_id("linkup", url),
                    title=str(item.get("name", "") or item.get("title", ""))[:300],
                    url=url,
                    publisher=publisher_of(url),
                    rank=i,
                    score=None,
                    snippet=str(item.get("content", "") or item.get("snippet", ""))[:600],
                )
            )
        return out[: max(req.effective_end(), req.count)]

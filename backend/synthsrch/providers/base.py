"""Unified search schema + adapter interface (search-ONLY, no router in V1)."""
from __future__ import annotations

import hashlib
from typing import Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str
    title: str = ""
    url: str
    publisher: str = ""
    rank: int = 0
    score: float | None = None
    snippet: str = ""


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    provider: str = "tavily"
    count: int = Field(default=10, ge=1, le=100)
    rank_start: int = Field(default=1, ge=1, le=200)
    rank_end: int | None = Field(default=None, ge=1, le=200)
    subtopics: list[str] = Field(default_factory=list, max_length=10)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    keyword_mode: str = "ANY"  # ANY|ALL

    def effective_end(self) -> int:
        if self.rank_end is None:
            return self.rank_start + self.count - 1
        return max(self.rank_start, self.rank_end)


PROVIDERS = ("tavily", "exa", "serper", "linkup", "firecrawl")


def publisher_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def result_id(provider: str, url: str) -> str:
    h = hashlib.sha256(f"{provider}:{url}".encode()).hexdigest()[:16]
    return f"{provider}-{h}"


def apply_keyword_filter(
    results: list[SearchResult], keywords: list[str], mode: str
) -> list[SearchResult]:
    """ANY = union, ALL = intersection (case-insensitive, title+snippet)."""
    kws = [k.strip().lower() for k in keywords if k.strip()]
    if not kws:
        return results
    mode = (mode or "ANY").upper()
    out: list[SearchResult] = []
    for r in results:
        hay = f"{r.title}\n{r.snippet}".lower()
        hits = [k for k in kws if k in hay]
        if mode == "ALL":
            if len(hits) == len(kws):
                out.append(r)
        else:
            if hits:
                out.append(r)
    return out


def slice_rank(results: list[SearchResult], start: int, end: int | None) -> list[SearchResult]:
    """1-based inclusive slice; re-numbers rank."""
    s = max(1, start) - 1
    e = end if end is not None else s + len(results)
    chunk = results[s:e]
    for i, r in enumerate(chunk, start=start):
        r.rank = i
    return chunk


class ProviderAdapter(Protocol):
    name: str
    async def search(self, req: SearchRequest) -> list[SearchResult]: ...
    # NOTE: no extract method — search APIs are search-only in V1.

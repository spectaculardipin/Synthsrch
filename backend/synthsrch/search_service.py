"""Manual provider dispatch — NO auto-router/fallback in V1."""
from __future__ import annotations

from .providers.base import PROVIDERS, SearchRequest, SearchResult
from .providers.exa import ExaAdapter
from .providers.firecrawl import FirecrawlAdapter
from .providers.linkup import LinkupAdapter
from .providers.serper import SerperAdapter
from .providers.tavily import TavilyAdapter

_ADAPTERS = {
    "tavily": TavilyAdapter(),
    "exa": ExaAdapter(),
    "serper": SerperAdapter(),
    "linkup": LinkupAdapter(),
    "firecrawl": FirecrawlAdapter(),
}


async def run_search(req: SearchRequest) -> tuple[list[SearchResult], str]:
    name = (req.provider or "tavily").lower()
    if name not in _ADAPTERS:
        raise ValueError(f"unknown provider '{req.provider}'. Choose one of: {', '.join(PROVIDERS)}")
    # No fallback: exactly the chosen provider, errors propagate with provider name.
    results = await _ADAPTERS[name].search(req)
    return results, name

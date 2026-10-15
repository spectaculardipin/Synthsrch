"""Silent sequential fallback router (V2) — requested first, then keyed others."""
from __future__ import annotations

import logging

from .providers.base import PROVIDERS, SearchRequest, SearchResult
from .providers.exa import ExaAdapter
from .providers.firecrawl import FirecrawlAdapter
from .providers.linkup import LinkupAdapter
from .providers.serper import SerperAdapter
from .providers.tavily import TavilyAdapter

log = logging.getLogger(__name__)

_ADAPTERS = {
    "tavily": TavilyAdapter(),
    "exa": ExaAdapter(),
    "serper": SerperAdapter(),
    "linkup": LinkupAdapter(),
    "firecrawl": FirecrawlAdapter(),
}

_KEY_ATTRS = {
    "tavily": "tavily_api_key",
    "exa": "exa_api_key",
    "serper": "serper_api_key",
    "linkup": "linkup_api_key",
    "firecrawl": "firecrawl_api_key",
}


def _has_key(provider: str) -> bool:
    from .config import get_settings

    attr = _KEY_ATTRS.get(provider, "")
    return bool(getattr(get_settings(), attr, "") or "")


def _fallback_order(requested: str) -> list[str]:
    req = (requested or "tavily").lower()
    if req == "auto":
        return [p for p in PROVIDERS if _has_key(p)]
    rest = [p for p in PROVIDERS if p != req and _has_key(p)]
    # Requested first only if it has a key; otherwise skip silently.
    head = [req] if _has_key(req) else []
    return head + rest


async def run_search(req: SearchRequest) -> tuple[list[SearchResult], str]:
    name = (req.provider or "tavily").lower()
    if name != "auto" and name not in _ADAPTERS:
        raise ValueError(f"unknown provider '{req.provider}'. Choose one of: {', '.join(PROVIDERS)} or 'auto'")
    order = _fallback_order(name)
    if not order:
        raise PermissionError(
            "no search API keys configured — add at least one provider key in Settings."
        )
    errors: list[str] = []
    for provider in order:
        try:
            results = await _ADAPTERS[provider].search(req)
            if provider != name:
                log.info("search fallback: %s → %s", name, provider)
            return results, provider
        except PermissionError as e:
            errors.append(str(e))
            continue
        except Exception as e:
            errors.append(f"{provider}: {e}")
            continue
    raise RuntimeError("all search providers failed: " + " | ".join(errors))

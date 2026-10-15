"""Router fallback — silent sequential try-next (V2)."""
import httpx
import pytest

from synthsrch.providers.base import SearchRequest
from synthsrch.search_service import run_search


def _ok(results):
    def _h(request):
        return httpx.Response(200, json=results)
    return httpx.AsyncClient(transport=httpx.MockTransport(_h))


async def test_requested_first_then_fallback_on_429(monkeypatch):
    import synthsrch.config as cfg
    import synthsrch.search_service as svc

    cfg.get_settings().tavily_api_key = "k1"
    cfg.get_settings().exa_api_key = "k2"
    cfg.get_settings().serper_api_key = ""
    cfg.get_settings().linkup_api_key = ""
    cfg.get_settings().firecrawl_api_key = ""

    async def fail_429(req):
        raise RuntimeError("tavily: provider error 429 — check key/credits.")

    async def ok_exa(req):
        from synthsrch.providers.base import SearchResult
        return [SearchResult(id="exa-abc", title="T", url="https://example.com", publisher="example.com", rank=1)]

    monkeypatch.setitem(svc._ADAPTERS, "tavily", type("A", (), {"name": "tavily", "search": staticmethod(fail_429)})())
    monkeypatch.setitem(svc._ADAPTERS, "exa", type("A", (), {"name": "exa", "search": staticmethod(ok_exa)})())

    results, used = await run_search(SearchRequest(query="q", provider="tavily"))
    assert used == "exa"
    assert results[0].id == "exa-abc"


async def test_missing_key_skipped_silently(monkeypatch):
    import synthsrch.config as cfg
    import synthsrch.search_service as svc

    cfg.get_settings().tavily_api_key = ""
    cfg.get_settings().exa_api_key = "k2"
    cfg.get_settings().serper_api_key = ""
    cfg.get_settings().linkup_api_key = ""
    cfg.get_settings().firecrawl_api_key = ""

    async def ok_exa(req):
        from synthsrch.providers.base import SearchResult
        return [SearchResult(id="exa-x", title="T", url="https://example.com/2", publisher="example.com", rank=1)]

    async def boom(req):
        raise AssertionError("tavily adapter should not be called without key")

    monkeypatch.setitem(svc._ADAPTERS, "tavily", type("A", (), {"name": "tavily", "search": staticmethod(boom)})())
    monkeypatch.setitem(svc._ADAPTERS, "exa", type("A", (), {"name": "exa", "search": staticmethod(ok_exa)})())

    results, used = await run_search(SearchRequest(query="q", provider="tavily"))
    assert used == "exa"


async def test_all_fail_raises_combined(monkeypatch):
    import synthsrch.config as cfg
    import synthsrch.search_service as svc

    cfg.get_settings().tavily_api_key = "k1"
    cfg.get_settings().exa_api_key = "k2"
    cfg.get_settings().serper_api_key = ""
    cfg.get_settings().linkup_api_key = ""
    cfg.get_settings().firecrawl_api_key = ""

    async def f1(req):
        raise RuntimeError("tavily: provider error 429")

    async def f2(req):
        raise RuntimeError("exa: provider error 500")

    monkeypatch.setitem(svc._ADAPTERS, "tavily", type("A", (), {"name": "tavily", "search": staticmethod(f1)})())
    monkeypatch.setitem(svc._ADAPTERS, "exa", type("A", (), {"name": "exa", "search": staticmethod(f2)})())

    with pytest.raises(RuntimeError, match="tavily|exa"):
        await run_search(SearchRequest(query="q", provider="tavily"))


async def test_unknown_provider_errors():
    with pytest.raises(ValueError):
        await run_search(SearchRequest(query="q", provider="nope"))

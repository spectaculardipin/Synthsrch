import httpx
import pytest

from synthsrch.extract import LocalExtractor
from synthsrch.providers.base import SearchRequest
from synthsrch.search_service import run_search


def _mock_search(handler):
    def _h(request):
        return httpx.Response(200, json=handler(request))
    return httpx.AsyncClient(transport=httpx.MockTransport(_h))


async def test_unknown_provider_errors():
    with pytest.raises(ValueError):
        await run_search(SearchRequest(query="q", provider="nope"))


async def test_tavily_search_only_no_raw_content(monkeypatch):
    from synthsrch.providers import tavily as tv
    import synthsrch.config as cfg

    cfg.get_settings().tavily_api_key = "tvly-test"
    seen = {}

    def handler(request):
        import json as j
        seen.update(j.loads(request.content.decode()))
        return {"results": [{"title": "T", "url": "https://example.com/a", "content": "snip", "score": 0.9}]}

    ad = tv.TavilyAdapter()
    out = await ad.search(SearchRequest(query="hello", provider="tavily"), client=_mock_search(handler))
    assert out[0].publisher == "example.com"
    assert seen.get("include_raw_content") is False
    assert "extract" not in str(seen).lower()


def test_extract_strips_media():
    ex = LocalExtractor()
    html = "<html><body><nav>nav</nav><article><h1>Hi</h1><p>Hello world text here.</p><img src=x><video></video></article></body></html>"
    text = ex.to_text_trafilatura(html)
    assert text is not None and "Hello world" in text
    assert "<img" not in text and "<video" not in text

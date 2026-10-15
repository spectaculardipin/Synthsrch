"""403/429 from plain fetch must fall through to the browser path."""
import httpx
import pytest

from synthsrch.extract import LocalExtractor


def _status_error(status: int, url: str) -> httpx.HTTPStatusError:
    req = httpx.Request("GET", url)
    resp = httpx.Response(status, request=req)
    return httpx.HTTPStatusError(f"Client error '{status}' for url '{url}'", request=req, response=resp)


async def test_403_falls_back_to_browser(monkeypatch):
    ex = LocalExtractor()
    url = "https://www.studocu.com/en-gb/document/x/y/1"

    async def blocked(self, u, client=None):
        raise _status_error(403, u)

    async def browser_ok(self, u):
        return "BROWSER TEXT " * 20

    monkeypatch.setattr(LocalExtractor, "fetch_html", blocked)
    monkeypatch.setattr(LocalExtractor, "to_text_crawl4ai", browser_ok)
    text, via = await ex.extract(url)
    assert via == "crawl4ai" and "BROWSER TEXT" in text


async def test_404_does_not_fall_back(monkeypatch):
    ex = LocalExtractor()
    called = []

    async def missing(self, u, client=None):
        raise _status_error(404, u)

    async def browser(self, u):
        called.append(u)
        return ("x" * 200, "crawl4ai")

    monkeypatch.setattr(LocalExtractor, "fetch_html", missing)
    monkeypatch.setattr(LocalExtractor, "to_text_crawl4ai", browser)
    with pytest.raises(httpx.HTTPStatusError):
        await ex.extract("https://example.com/gone")
    assert called == []


async def test_403_browser_also_fails_reports_blocked(monkeypatch):
    ex = LocalExtractor()

    async def blocked(self, u, client=None):
        raise _status_error(403, u)

    async def browser_empty(self, u):
        raise RuntimeError("crawl4ai returned empty content")

    monkeypatch.setattr(LocalExtractor, "fetch_html", blocked)
    monkeypatch.setattr(LocalExtractor, "to_text_crawl4ai", browser_empty)
    with pytest.raises(RuntimeError, match="refused|blocked|403"):
        await ex.extract("https://www.studocu.com/x")

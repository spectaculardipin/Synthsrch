"""Local-only clean-text extraction: httpx + trafilatura primary, crawl4ai fallback."""
from __future__ import annotations

import re

import httpx
import trafilatura

from .config import get_settings

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Synthsrch/0.1"

_TAG_RE = re.compile(r"<(img|video|iframe|script|style|canvas|svg)[^>]*>.*?</\1>|<(img|video|iframe)[^>]*/?>", re.IGNORECASE | re.DOTALL)


class LocalExtractor:
    async def fetch_html(self, url: str, client: httpx.AsyncClient | None = None) -> str:
        own = client is None
        c = client or httpx.AsyncClient(
            timeout=get_settings().extract_timeout_s, follow_redirects=True, headers={"User-Agent": UA}
        )
        try:
            r = await c.get(url)
            r.raise_for_status()
            return r.text
        finally:
            if own:
                await c.aclose()

    def to_text_trafilatura(self, html: str, url: str = "") -> str | None:
        try:
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                include_links=False,
                favor_precision=True,
            )
        except Exception:
            return None
        if not text:
            return None
        text = _TAG_RE.sub("", text).strip()
        return text or None

    async def to_text_crawl4ai(self, url: str) -> str:
        """Fallback for JS-heavy pages. Import lazily so backend works without browser deps."""
        try:
            from crawl4ai import AsyncWebCrawler  # type: ignore
        except Exception as e:
            raise RuntimeError(f"crawl4ai unavailable: {e}")
        async with AsyncWebCrawler() as crawler:
            res = await crawler.arun(url=url)
            md = getattr(res, "fit_markdown", None) or getattr(res, "markdown", "") or ""
            text = _TAG_RE.sub("", str(md)).strip()
            if not text:
                raise RuntimeError("crawl4ai returned empty content")
            return text

    async def extract(self, url: str, max_chars: int | None = None) -> tuple[str, str]:
        """Returns (text, via). Raises on failure."""
        cap = max_chars or get_settings().extract_max_chars
        html = await self.fetch_html(url)
        text = self.to_text_trafilatura(html, url)
        via = "trafilatura"
        if not text or len(text.strip()) < 200:
            text = await self.to_text_crawl4ai(url)
            via = "crawl4ai"
        return text[:cap], via

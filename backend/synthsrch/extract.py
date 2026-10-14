"""Local-only clean-text extraction: httpx + trafilatura primary, crawl4ai fallback."""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from .config import get_settings

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Synthsrch/0.1"
MAX_REDIRECTS = 3
MAX_BODY_BYTES = 10_000_000
# Cap concurrent browser extractions: each crawl4ai run launches a full
# Chromium. Unbounded parallelism (e.g. 10 background pre-extracts) would
# exhaust low-end laptops — the app's core audience.
_CRAWL_SEMAPHORE = None


def _crawl_semaphore() -> asyncio.Semaphore:
    global _CRAWL_SEMAPHORE
    if _CRAWL_SEMAPHORE is None:
        _CRAWL_SEMAPHORE = asyncio.Semaphore(2)
    return _CRAWL_SEMAPHORE

_TAG_RE = re.compile(r"<(img|video|iframe|script|style|canvas|svg)[^>]*>.*?</\1>|<(img|video|iframe)[^>]*/?>", re.IGNORECASE | re.DOTALL)


def _is_public_ip(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_public_url(url: str) -> str:
    """Allowlist guard against SSRF: only public http(s) URLs may be fetched.

    Rejects non-http(s) schemes, empty/unresolvable hosts, literal non-public
    IPs (no DNS needed), `localhost`, and any hostname resolving (via ALL
    A/AAAA records) to a non-public address — including the 169.254.169.254
    cloud-metadata address. Raises ValueError; returns the URL unchanged.

    Known residual: DNS-rebinding TOCTOU between check and fetch. Acceptable
    for a single-user localhost tool; a shared deployment needs a filtering
    egress proxy instead.
    """
    try:
        parts = urlparse((url or "").strip())
    except Exception:
        raise ValueError("extract blocked: malformed URL")
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"extract blocked: scheme '{parts.scheme or '(none)'}' not allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("extract blocked: empty host")
    # Fast path: literal IP needs no DNS.
    try:
        ipaddress.ip_address(host.strip("[]") if host.startswith("[") else host)
    except ValueError:
        pass
    else:
        if not _is_public_ip(host.strip("[]") if host.startswith("[") else host):
            raise ValueError("extract blocked: non-public IP literal")
        return url
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("extract blocked: localhost")
    try:
        infos = socket.getaddrinfo(host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError("extract blocked: DNS resolution failed")
    ips = {info[4][0] for info in infos if info[4]}
    if not ips or not all(_is_public_ip(ip) for ip in ips):
        raise ValueError("extract blocked: host resolves to non-public address")
    return url


class LocalExtractor:
    async def fetch_html(self, url: str, client: httpx.AsyncClient | None = None) -> str:
        # SSRF guard on the entry URL and on every redirect hop (no auto-follow).
        target = assert_public_url(url)
        own = client is None
        c = client or httpx.AsyncClient(
            timeout=get_settings().extract_timeout_s, follow_redirects=False, headers={"User-Agent": UA}
        )
        try:
            for _ in range(MAX_REDIRECTS + 1):
                r = await c.get(target)
                loc = r.headers.get("location")
                if r.status_code in (301, 302, 303, 307, 308) and loc:
                    target = assert_public_url(urljoin(target, loc))
                    continue
                r.raise_for_status()
                if len(r.content) > MAX_BODY_BYTES:
                    raise RuntimeError("page too large to extract")
                return r.text
            raise RuntimeError("too many redirects")
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

    async def extract(self, url: str, max_chars: int | None = None, allow_fallback: bool = True) -> tuple[str, str]:
        """Returns (text, via). Raises on failure.

        allow_fallback=False restricts to the fast trafilatura path (bounded,
        no browser) — used for on-demand gap fills inside latency-sensitive flows.
        """
        assert_public_url(url)  # single choke point: covers trafilatura and crawl4ai paths
        cap = max_chars or get_settings().extract_max_chars
        html = await self.fetch_html(url)
        text = self.to_text_trafilatura(html, url)
        via = "trafilatura"
        # Short-but-complete pages (e.g. example.com ≈ 150 chars) must NOT take
        # the slow browser path. Only near-empty results (<100) trigger it —
        # JS-rendered pages typically yield None here.
        if allow_fallback and (not text or len(text.strip()) < 100):
            async with _crawl_semaphore():
                text = await self.to_text_crawl4ai(url)
            via = "crawl4ai"
        if not text:
            raise RuntimeError("trafilatura returned empty content")
        return text[:cap], via

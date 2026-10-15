# ADR-003: Browser fallback on soft-block HTTP statuses

## Status
Accepted

## Date
2026-10-15

## Context
Local extraction fetches pages with plain httpx. Sites with bot detection
(studocu, academia.edu, researchgate, instagram) answer `403` to that fetch,
and the old pipeline raised immediately — the crawl4ai/Chromium fallback only
ran for empty text, never for HTTP errors. Verified live: studocu 403s httpx
but extracts fine through Chromium.

## Decision
On `401/403/429` from the plain fetch, fall through to the crawl4ai browser
path (same 2-concurrency semaphore as before). `404`/DNS/SSRF-guard failures
still fail fast — retrying those in a browser buys nothing. If the browser
also fails, the error says the site is login-walled or bot-blocked and names
another source as the remedy.

## Alternatives Considered
- **Rotating user agents / header spoofing:** an arms race against bot
  vendors; rejected — the real browser already carries a genuine fingerprint.
- **Browser-first for everything:** ~4s per page and heavy on low-end
  laptops; rejected — fast path stays default, browser stays fallback.
- **Using provider extract APIs (Tavily Extract etc.):** costs money per page
  and moves page content to a third party; rejected — extraction stays
  local-only per the project's core rule.

## Consequences
- Login-walled bodies (studocu full text) still yield only preview text —
  the page, not the vault.
- The latency-sensitive chat gap-fill keeps `allow_fallback=False`;
  background pre-extract and drawer adds use the full pipeline.

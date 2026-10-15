# ADR-002: Claude-grade chat — markdown, session sidebar, sources drawer

## Status
Accepted

## Date
2026-10-15

## Context
V1 chat rendered assistant text as plain paragraphs, kept sessions on a
separate History page, and froze the source list at export time. Long answers
with headings, lists, and code were hard to scan; resuming work took two
page hops; a dead source mid-chat meant starting over.

## Decision
- **Markdown rendering** (`react-markdown` + GFM + `rehype-sanitize`, no
  `allowDangerousHtml`): headings, bullets, code, tables. Citation markers
  (`[S1]`, `[S1, S3]`) tokenize into tiny inline `<sup>` badges with
  `p → fragment` rendering so badges never break paragraph flow.
- **Session sidebar replaces the History page** for chats: list, resume,
  per-chat delete, clear-all (two-tap confirm). Search history stays out of
  the way; chat is always one click away (no export gate to open it).
- **Sources drawer** (`PATCH /api/sessions/{id}/sources`): Current /
  Last-results / New-search / Paste-URL tabs. Adds re-extract automatically;
  removes apply to the next message immediately. Pasted URLs get a
  `pasted-…` cache row like any other source.
- **Blocked-until-grounded:** a sourceless chat shows one minimal state
  ("You haven't added any sources yet → Search for sources") instead of a
  dead composer — chat quality is defined by grounding.
- **Minimal model widget** in the chat header lists only pre-entered
  key+model pairs (`GET /api/models → configured`); picking one sets provider
  *and* its own model together, so a provider can never be called with
  another provider's model ID.

## Alternatives Considered
- **Keeping the History page:** an extra hop for the core resume flow;
  rejected.
- **Free chat without sources:** tried, then removed — uncited answers
  contradict the product's purpose; the empty state funnels to search.
- **Full model catalog dropdown:** rots monthly; rejected in favor of
  free-text IDs + per-provider saved models.

## Consequences
- `HistoryView` removed; session messages persist `user/assistant/notice`
  roles (`notice` = router-switch pills).
- All provider/user-supplied URLs render as links only through `safeUrl()`
  (http(s) allowlist) — `javascript:`/`data:` hrefs render as text.

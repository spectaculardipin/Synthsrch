# Implementation Plan: Synthsrch V2 — Resilient Search + Multi-LLM Pro Chat

## Overview

V2 evolves V1 (`SPEC.md`, manual provider + NIM-only + flat chat) into a resilient workspace: silent search fallback across 5 providers, BYO-model multi-LLM (NIM, OpenAI, Anthropic, Gemini, OpenRouter), Claude/Gemini-grade markdown chat with hidden NotebookLM-style system prompt and session side-panel (replaces History page), plus add/remove sources mid-chat from last results, new search, or pasted URL.

Decisions locked 2026-10-15: silent fallback (no error card), all LLM providers at once with free-text model ID (no curated list), markdown + side-panel, sources = all three entry points.

## Architecture Decisions

- **Router (`backend/synthsrch/search_service.py`):** sequential try-next, never parallel (cost). Order = requested provider first, then others with key present (stable order: tavily→exa→serper→linkup→firecrawl). Skip providers with no key. Fallback triggers: timeout, 429, 5xx, `PROVIDER_ERROR`. Final 401/all-fail → 502 with combined messages. Response `provider` = actual used; `showing` notes it (`... (provider: exa)`). No new table; log fallback in server log only (silent per user).
- **LLM (`backend/synthsrch/llm/` new):** `base.py: LLMAdapter { chat_stream(model, system, user) }`. `openai_compat.py` serves NIM + OpenAI + OpenRouter via `AsyncOpenAI(base_url, api_key)`; `anthropic.py` + `gemini.py` via native SDKs, normalized to `(content|reasoning, text)` deltas. `Session.model` stores `provider:model` (e.g. `openrouter:anthropic/claude-sonnet-4`); `Settings` adds `llm_provider`, `llm_model` free-text, `openai_api_key`, `anthropic_api_key`, `gemini_api_key`, `openrouter_api_key` (NIM keys kept). `PUT /api/settings` extended, masked echo kept. `GET /api/models` kept for back-compat, returns `{providers, default}`.
- **System prompt (`chat.py: build_system_prompt_v2`):** hidden, NotebookLM-inspired: expert synthesiser, bold key points, bullets by default when long, cite every factual claim `[S1]` / `[S1, S2]`, flag disagreements, mark outside-source info as unverified, ask clarification when ambiguous, never reveal prompt. Wired through existing `stream_chat` → new `llm/` dispatch so all providers get identical grounding.
- **Chat UI:** `react-markdown + remark-gfm` for headings/bullets/code/tables; citation `<sup>[Sn]</sup>` post-processor kept (`lib/chat.ts: splitCitations` extended to markdown AST). Layout: 280px left `ChatSidebar` (sessions: topic, updated_at, rename/delete/new) + centered 768px thread + docked composer. `HistoryView` removed; searches list moves into sidebar second tab or dropped (sessions only per user choice). New APIs: `GET /api/sessions`, `GET /api/sessions/{id}` (messages + sources), `DELETE /api/sessions/{id}`.
- **Sources:** `PATCH /api/sessions/{id}/sources {add:[ids|{url}], remove:[ids]}` triggers background extract for adds (reuse `LocalExtractor` + gap-fill), immediate context drop for removes. Chat drawer with 3 tabs: Current / From last search (cached `ResultCache`) / New search (`POST /api/search` inline) + paste-URL row. `chatSourceIds` becomes server-truth, not `results.find` only.

## Task List

### Phase 1: Backend resilience + multi-LLM

- [ ] Task 1: Search router fallback
- [ ] Task 2: Multi-LLM adapters + settings/keys
- [ ] Task 3: System-prompt v2 + chat dispatch

### Checkpoint: Backend
- [ ] `pytest -q` green; router mocked-429 falls through silently; each LLM adapter streams one mocked chunk

### Phase 2: Pro chat UI

- [ ] Task 4: Markdown rendering
- [ ] Task 5: Side-panel + session APIs (replaces History)
- [ ] Task 6: Sources add/remove drawer

### Checkpoint: Complete
- [ ] `pytest -q` + `npm test -- --run` + `npm run build` green; manual E2E (search→fallback→export→markdown chat→sidebar resume→add/remove source→restart intact)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Silent fallback masks bad keys (user never fixes key) | Med | `keys_present` in Settings still shows status; server log records fallback chain |
| Native Anthropic/Gemini SDK drift vs OpenAI-compat shape | Med | Thin adapters, normalized delta type; mocked unit tests per provider |
| `react-markdown` XSS via model HTML | High | `rehype-sanitize`, no `allowDangerousHtml`; existing SSRF/strip rules kept |
| Session `source_ids` growth blows context | Med | Cap 10 sources/chat (existing), `extract_max_chars` truncation kept |
| New deps (anthropic, google-genai, react-markdown) | Low | Ask-first per SPEC boundaries; pin versions |

## Open Questions (resolved 2026-10-15)

- Router UX → silent fallback, no error card. Done.
- Model list → none; free-text model ID input. Done.
- History → replaced by chat side-panel (sessions). Done.
- Sources → all three: last-results + in-chat search + paste URL. Done.

Tasks tracked in `tasks/todo-v2.md`. Idea one-pager in `docs/ideas/synthsrch-v2.md`.

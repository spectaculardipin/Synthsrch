# Todo: Synthsrch V2

## Task 1: Search router — silent sequential fallback

**Description:** Replace manual-only dispatch in `search_service.py` with try-next fallback over key-configured providers.

**Acceptance criteria:**
- [ ] Requested provider tried first; on timeout/429/5xx auto-tries next key-present provider silently
- [ ] Response `provider` = actual used; all-fail returns 502 with combined provider messages
- [ ] No parallel fan-out (single provider billed per search)

**Verification:**
- [ ] Tests pass: `pytest -q tests/backend/test_router_fallback.py` (mocked 429 → fallback, no-key skip)
- [ ] Build succeeds: `python -m build` (or at least import check)
- [ ] Manual check: disable tavily key → search still returns with `(provider: exa)`

**Dependencies:** None

**Files likely touched:**
- `backend/synthsrch/search_service.py`
- `backend/synthsrch/providers/base.py`
- `tests/backend/test_router_fallback.py`

**Estimated scope:** Medium: 3-5 files

## Task 2: Multi-LLM adapters + settings keys

**Description:** Add provider-agnostic LLM layer (NIM, OpenAI, Anthropic, Gemini, OpenRouter) with free-text model ID and per-provider keys.

**Acceptance criteria:**
- [ ] `llm/base.py + openai_compat.py + anthropic.py + gemini.py` stream normalized deltas
- [ ] Settings stores 4 new keys + `llm_provider` + `llm_model` free-text; masked echo; hydrate on restart
- [ ] Chat uses `provider:model` from session, not NIM-only

**Verification:**
- [ ] Tests pass: `pytest -q tests/backend/test_llm_adapters.py` (mocked stream per provider)
- [ ] Manual check: save OpenRouter key + type model ID → chat streams

**Dependencies:** None (parallel with Task 1)

**Files likely touched:**
- `backend/synthsrch/llm/*.py`
- `backend/synthsrch/config.py`
- `backend/synthsrch/app.py` (`/api/settings`, `/api/models`)
- `backend/synthsrch/models.py` (session provider field if needed)

**Estimated scope:** Medium: 3-5 files

## Task 3: Hidden system-prompt v2 + chat dispatch

**Description:** NotebookLM-style hidden prompt (grounding, citations, bold/bullets default, outside-source flag, clarification) wired to all LLM adapters.

**Acceptance criteria:**
- [ ] `build_system_prompt_v2(topic, purpose, kws, n)` used for every chat; old builder removed or delegated
- [ ] Prompt carries excerpts (existing gap-fill kept), `[S1..Sn]` refs, disagreement/insufficient handling
- [ ] No prompt leak in UI or logs

**Verification:**
- [ ] Tests pass: `pytest -q tests/backend/test_chat_prompt.py` (assert cites, bullets-default, outside-source clause)
- [ ] Manual check: chat answer contains `[S1]` citations and bullet formatting

**Dependencies:** Task 2

**Files likely touched:**
- `backend/synthsrch/chat.py`
- `backend/synthsrch/app.py` (`/api/sessions/{sid}/chat`)
- `tests/backend/test_chat_prompt.py`

**Estimated scope:** Small: 1-2 files

## Checkpoint: Backend

- [ ] All tests pass (`pytest -q`)
- [ ] Router + LLM + prompt verified mocked
- [ ] Review with human before UI work

## Task 4: Pro chat rendering (markdown)

**Description:** Claude/Gemini-grade message rendering: headings, bullets, code, tables via react-markdown + GFM + sanitize, citation sup preserved.

**Acceptance criteria:**
- [ ] Assistant messages render markdown (titles, bullets, code blocks, tables)
- [ ] `[S1]` renders as sup badge; streaming caret + Thinking block kept
- [ ] No raw HTML injection (`rehype-sanitize`)

**Verification:**
- [ ] Tests pass: `cd frontend; npm test -- --run`
- [ ] Build succeeds: `cd frontend; npm run build`
- [ ] Manual check: long answer shows headings + bullets + cited sups

**Dependencies:** Task 3

**Files likely touched:**
- `frontend/src/components/ChatView.tsx`
- `frontend/src/lib/chat.ts`
- `frontend/package.json`

**Estimated scope:** Small: 1-2 files

## Task 5: Chat side-panel + session APIs (replaces History)

**Description:** Left session sidebar (list/resume/new/rename/delete) replacing History page; new session fetch APIs.

**Acceptance criteria:**
- [ ] Sidebar lists sessions, click resumes full log + sources + header
- [ ] `GET /api/sessions`, `GET /api/sessions/{id}`, `DELETE /api/sessions/{id}` work; restart-proof
- [ ] `HistoryView` removed from nav; searches accessible or explicitly dropped

**Verification:**
- [ ] Tests pass: `pytest -q tests/backend/test_sessions_api.py`
- [ ] Manual check: new chat → sidebar → reload → resume same thread

**Dependencies:** Task 4

**Files likely touched:**
- `frontend/src/components/ChatSidebar.tsx` (new)
- `frontend/src/App.tsx`
- `backend/synthsrch/app.py`
- `frontend/src/views/HistoryView.tsx` (remove)

**Estimated scope:** Medium: 3-5 files

## Task 6: Sources add/remove mid-chat

**Description:** Drawer to manage session sources: current/remove, from-last-search add, in-chat new search, paste URL; auto re-extract on add.

**Acceptance criteria:**
- [ ] `PATCH /api/sessions/{id}/sources` add/remove persists; chat context updates immediately
- [ ] Drawer supports all three: cached results, inline search, URL paste with extract status
- [ ] Send gating (extracting…) still guarantees excerpts

**Verification:**
- [ ] Tests pass: `pytest -q tests/backend/test_session_sources.py`
- [ ] Manual check: remove S1 → next answer cites only S2+; add pasted URL → cited as Sn

**Dependencies:** Task 5

**Files likely touched:**
- `backend/synthsrch/app.py`
- `frontend/src/components/SourcesDrawer.tsx` (new)
- `frontend/src/App.tsx`

**Estimated scope:** Medium: 3-5 files

## Checkpoint: Complete

- [ ] All acceptance criteria met
- [ ] `pytest -q` + `npm test -- --run` + `npm run build` green
- [ ] E2E: search (fallback) → export → markdown chat → sidebar resume → add/remove source → restart intact
- [ ] Ready for review — no build started until approved

# Spec: Synthsrch V1 — Local Search & Knowledge Synthesis

## Objective

Build **Synthsrch**, a local-first, open-source search + synthesis app for Windows that runs as `synthsrch` on the terminal and opens a localhost web UI. It solves two problems:

1. **Browser-tool friction:** lag on low-end laptops, subscriptions, code-exposure risk. All orchestration runs on `127.0.0.1`; only provider API calls leave the machine.
2. **AI-chat clutter:** long flat chats lose focus. Synthsrch keeps research structured: search → select sources (checkbox cards) → export to a JSON-prompted chat (`topic`, `purpose`, `domainKeywords`) with inline `[Sn]` citations and a persistent sources rail.

**Users:** solo researcher/developer on Windows, comfortable with API keys and terminal.

**V1 scope decisions (per user, 2026-10-14):**

- All **5 search providers configurable** in V1: Tavily, Exa, Serper, Linkup, Firecrawl. User picks **one provider per search** via selector. **No auto-router/fallback in V1** (explicit non-goal; planned V2).
- **LLM = NVIDIA NIM only** (`https://integrate.api.nvidia.com/v1`, OpenAI-compatible). User can **select from a range of NIM models** + custom model string.
- **Persistent history** in local SQLite (searches, chats, settings survive restarts).

**User stories:**

- US1: I run `PS C:\Users\ghimi> synthsrch` and a browser tab opens with Synthsrch; no Docker, no manual server steps.
- US2: I type a query, choose provider + result count + rank bracket (e.g. 20–40), see note-style rounded cards (publisher + title + `#rank` + checkbox), click a card to read clean raw text (no images/video).
- US3: I add sub-topics / keywords with ANY|ALL match to filter within current results.
- US4: I check 2–5 cards, export to chat with `{topic, purpose, domainKeywords}`, chat with NIM grounded on those sources, add/remove sources mid-chat.
- US5: I see my past searches and chat sessions in History, persisted across restarts.
- US6: I paste my own keys for all 5 search providers + NIM key in Settings; keys never leave disk except to the chosen provider.

## Capability Map

Single initiative, five independently testable modules:

| Module id | Responsibility | Depends on |
|---|---|---|
| `launcher` | `synthsrch` CLI, local server lifecycle, browser open | — |
| `search-providers` | 5 provider adapters + manual selector, unified result schema | `launcher` |
| `extract` | Clean text extraction local-only (httpx + trafilatura primary, crawl4ai fallback; search APIs never used for crawl/extract) | `search-providers` |
| `structured-chat` | JSON-prompted NIM chat grounded on selected sources | `extract` |
| `history-settings` | Persistent SQLite history + key/model settings UI | `launcher` |

Build order: `launcher` → `history-settings` → `search-providers` → `extract` → `structured-chat`.

> Note (v1): the Obsidian-style knowledge-graph module was removed from scope
> entirely (backend endpoints, tables, and UI). No graph code remains.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI `>=0.115`, Uvicorn `>=0.30`, httpx `>=0.27`, Pydantic `>=2.7` + pydantic-settings, SQLAlchemy `>=2.0` + aiosqlite, trafilatura `>=1.10` (extract primary), crawl4ai `>=0.6` (extract fallback for JS-heavy pages), `openai>=1.40` SDK pointed at NIM, python-keyring (optional OS keyring, fallback encrypted file).
- **Provider rule:** search APIs (Tavily/Exa/Serper/Linkup/Firecrawl) are used for **searching only** (`title/url/snippet/score`). Never call provider extract/crawl/scrape (`include_raw_content`, `/extract`, `/contents`, `scrapeOptions`) in V1.
- **Frontend:** Vite `>=6`, React `18` + TypeScript `~5.5`, Tailwind `~3.4`, fetch + SSE for NIM streaming. Built to `backend/synthsrch/static/` and served by FastAPI (single process, low RAM).
- **LLM:** NVIDIA NIM cloud, `base_url=https://integrate.api.nvidia.com/v1`, `POST /v1/chat/completions`, `GET /v1/models`. No local inference in V1.
- **DB:** SQLite file at `%APPDATA%\synthsrch\synthsrch.db` (fallback `~/.synthsrch/synthsrch.db`).
- **Packaging:** `pyproject.toml` with `console_scripts synthsrch`, `pipx install .` supported, `install.ps1` for PATH.

Why: FastAPI + static Vite = one Windows process, minimal RAM (matches `farfalle`/`searcharvester` precedent, lighter than Next.js server). SQLite = zero-service persistence.

## Commands

```powershell
# install (from repo root)
pip install -e .
# or isolated
pipx install .

# run — opens http://127.0.0.1:8765
synthsrch
synthsrch --port 8765 --no-browser
synthsrch --help
synthsrch doctor        # checks python version, port, db path, NIM reachability

# dev
python -m synthsrch --port 8765          # backend dev (serves API + static if built)
cd frontend; npm install; npm run dev    # frontend dev (proxy /api -> :8765)

# build / test / lint
python -m build
pytest -q                                # backend: pytest + httpx AsyncClient
cd frontend; npm test -- --run           # frontend: vitest
cd frontend; npm run build               # emits to backend/synthsrch/static
ruff check . && ruff format --check .
mypy backend/synthsrch
```

## Project Structure

```
SPEC.md                        → this file (source of truth)
backend/
  pyproject.toml               → package + synthsrch entrypoint
  synthsrch/
    __main__.py                → CLI (port pick, uvicorn run, webbrowser.open)
    app.py                     → FastAPI app, static mount, CORS localhost-only
    config.py                  → pydantic-settings, db path, NIM base_url
    db.py / models.py          → SQLAlchemy models, session
    providers/
      base.py                  → Unified SearchResult + ProviderAdapter interface
      tavily.py exa.py serper.py linkup.py firecrawl.py
    extract.py                 → local-only clean text (httpx fetch + trafilatura primary, crawl4ai fallback; no provider extract)
    chat.py                    → JSON prompt builder + NIM streaming via openai SDK
    static/                    → built frontend (generated, committed for v1)
frontend/
  src/components/ SearchBar/ ResultCard/ FilterPanel/ ChatPanel/ Settings/
  src/lib/ api.ts types.ts
tests/backend/                 → test_filter_slice, test_chat_prompt, test_providers_extract, test_settings_persist, test_search_upsert
tests/frontend/  (vitest)      → filter ANY|ALL, rank slice
install.ps1                    → Windows PATH + first-run helper
docs/                          → provider key links, NIM model list
```

## Code Style

Type-safe boundaries, validate at edges, flat errors. Example adapter contract:

```python
# backend/synthsrch/providers/base.py
from pydantic import BaseModel, HttpUrl

class SearchResult(BaseModel):
    id: str            # provider:url hash
    title: str
    url: HttpUrl
    publisher: str     # hostname
    rank: int          # 1-based after slice
    score: float | None = None
    snippet: str = ""

class SearchRequest(BaseModel):
    query: str
    provider: str      # tavily|exa|serper|linkup|firecrawl — manual, no auto-fallback in V1
    count: int = 10
    rank_start: int = 1
    rank_end: int | None = None
    subtopics: list[str] = []
    keywords: list[str] = []
    keyword_mode: str = "ANY"  # ANY|ALL

class ProviderAdapter:
    name: str
    async def search(self, req: SearchRequest) -> list[SearchResult]: ...
    # NOTE: no extract method — search APIs are search-only in V1.

# backend/synthsrch/extract.py — local-only extraction
class LocalExtractor:
    async def fetch_html(self, url: str) -> str: ...       # httpx, 15s timeout, UA rotation
    def to_text_trafilatura(self, html: str, url: str) -> str | None: ...
    async def to_text_crawl4ai(self, url: str) -> str: ...  # fallback for JS-heavy pages
```

Conventions: `snake_case` Python, `camelCase` TS/JSON, REST plural nouns (`GET /api/searches`, `POST /api/search`), errors `{error:{code,message}}`, semantic Tailwind tokens only, no raw hex in components.

## Testing Strategy

- **Backend (pytest):** adapter normalization per provider (mocked httpx, search-only — assert no extract/crawl params sent), rank-slice logic (`rank_start/rank_end`), keyword ANY|ALL filter, local extract strips `<img>/<video>/nav` via trafilatura, crawl4ai fallback mocked, chat prompt contains `topic/purpose/domainKeywords/sources`, settings persist + hydrate across restarts, repeat-search upsert. Target ≥70% on `providers/`, `extract.py`, `chat.py`.
- **Frontend (vitest):** filter reducer, rank badge, checkbox selection set, settings key-masking.
- **Manual E2E per slice:** `synthsrch` → search (each of 5 providers once) → open card text → export → chat streams → restart → history intact.
- **No live-key CI:** live provider/NIM tests behind `SYNTHSRCH_LIVE=1`, never in default run.

## Boundaries

- Always: validate provider + NIM responses as untrusted (Pydantic parse, timeout 15s search / 60s extract); never log full API keys (mask `tvly-***`); run `pytest -q` before commit; bind `127.0.0.1` only by default; strip images/video/scripts in extract.
- Ask first: adding a dependency, changing SQLite schema, changing default port (8765), adding telemetry (default: none).
- Never: commit keys/`.env`, implement V1 auto-router/fallback (explicitly deferred to V2), use search-provider extract/crawl/scrape in V1, add cloud sync/accounts, use local GPU inference in V1, edit `backend/synthsrch/static/` by hand.

## Functional Spec (V1)

### 1. Launcher (`launcher`)

- `synthsrch` picks port (default 8765, next-free if busy), starts Uvicorn on `127.0.0.1`, opens default browser. `--no-browser` skips open. `doctor` reports python/port/db/NIM DNS.
- Success: cold `synthsrch` → usable UI in <10s on HDD-class laptop (excluding npm install).

### 2. Search (`search-providers`)

- Search bar (landing + results header) + gear panel: `provider` dropdown (5), `count` (1–100, clamped per provider cap), `rank_start–rank_end` (e.g. 20–40), `keywords` + `ANY|ALL`, `subtopics` (search-within box).
- Provider caps handled client-visible: Tavily `max_results≤20`, Exa `numResults≤100`, Serper `num≤100 + page`, Linkup `depth standard` default, Firecrawl `limit`. If `rank_end` exceeds one call, backend fans out (parallel page queries where supported, else single max fetch) then slices; UI shows `Showing ranks X–Y of ~Z (provider: N)`.
- Cards: 3-col grid, `rounded-2xl` note boxes, `publisher` top-left, checkbox top-right, title+2-line snippet, `#rank` bottom-right. Second row: `Search within these results` input (filters in-memory; `Search web for sub-topic` button re-queries with `query + subtopic`).
- No router: invalid/missing key for chosen provider → `402/401` error card naming that provider + link to Settings. No silent switch.

### 3. Extract (`extract`) — local-only, search APIs never used

- Click card → drawer fetches `POST /api/extract {url, query}`. Pipeline is strictly local: `httpx GET (15s timeout, desktop UA, follow redirects)` → `trafilatura` primary (`include_tables=True, include_links=False, no_fallback=False`) → if empty/<200 chars, fallback `crawl4ai` (`c4ai.AsyncWebCrawler`, fit_markdown) for JS-heavy pages. No `Tavily Extract`, `Exa /contents`, `Firecrawl /scrape`, `Linkup /fetch`, `Serper scrape` calls in V1.
- Output plain text with headings/lists preserved, zero `<img>/<video>/iframe/script>` in stored text and rendered DOM.
- Shows `source url • publisher • extracted N chars • via {trafilatura|crawl4ai}`.

### 4. Structured chat (`structured-chat`)

- Select via checkboxes → `Export N → Chat` creates session with header form: `topic*`, `purpose*`, `domainKeywords[]`, source list (add/remove anytime), model input with suggestions (see §5).
- System prompt built deterministically:
  `You are Synthsrch synthesiser. Topic:{topic}. Purpose:{purpose}. DomainKeywords:{...}. Ground EVERY claim in [S1..Sn] excerpts; cite [Sn]; if sources disagree say so; if insufficient say so.`
  User query + excerpts (truncated to model context) → NIM `stream:true` SSE. Follow-ups retain same header unless edited.
- Persist `sessions/messages` in SQLite.

### 5. NIM models (`history-settings` part)

- Settings fields: `NIM_API_KEY`, `NIM_MODEL` text input with datalist suggestions + custom allowed, `NIM_BASE_URL` (default cloud). V1 curated list (all via same `/v1/chat/completions`):
  `meta/llama-3.1-8b-instruct` (fast/default), `meta/llama-3.1-70b-instruct`, `meta/llama-3.1-405b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`, `mistralai/mixtral-8x22b-instruct-v0.1`, `qwen/qwen2.5-72b-instruct`, `google/gemma-2-9b-it`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b` + `custom…`. `GET /v1/models` validates at save; per-model `max_tokens` default 1024.
- Chat header and Settings stay in sync on the selected model.

### 6. History + Settings persistence

- SQLite tables: `searches, results_cache, sessions, messages, settings`. Restart-proof. `History` page lists searches/sessions with re-open + delete. Keys stored via OS keyring if available else file with restricted ACL; UI masks keys.

## Success Criteria (V1 done when)

- [ ] `pip install -e . && synthsrch` opens UI; `synthsrch doctor` passes offline.
- [ ] Each of 5 providers returns cards with correct publisher/title/rank; count + rank bracket (incl. 20–40 where provider allows) slices correctly.
- [ ] Card click shows local-only text extract (`via trafilatura|crawl4ai`), no images/video tags in DOM, no provider extract API called.
- [ ] Keyword ANY returns union, ALL returns intersection (unit-tested).
- [ ] Export 3 sources → chat streams cited NIM answer; changing model in header changes `model` in NIM request.
- [ ] Restart preserves history; missing-key provider shows clear error, does NOT call another provider.
- [ ] `pytest -q` + `npm test -- --run` + `npm run build` green.

## Open Questions

- Q1: Default NIM model for first run — keep `llama-3.1-8b-instruct` (fast) or `70b` (quality)?
- Q2: DB location — approve `%APPDATA%\synthsrch\` (vs repo-local `./data/`)?
- Q3: For rank brackets beyond a provider cap (e.g. Tavily 41–60), is multi-query fan-out acceptable in V1, or cap UI at provider max with notice?
- Q4: Extract length cap per source for NIM context (e.g. 6k chars) — acceptable default?

---
*References reused: `rashadphz/farfalle`, `vakovalskii/searcharvester`, `AnyGenIO/anygen-search-cli`, `X27/X-Local-Search`, `ItzCrazyKns/Vane`, `adityaparab/trawl`, `pr1m8/perplexity-at-home`. Provider docs: Tavily search/extract, Exa search/contents, Firecrawl search/scrape, Serper, Linkup `/v1/search`; NIM OpenAI-compatible `/v1/chat/completions`.*

# Synthsrch V2 — Learn without clutter, resiliently

## Problem Statement

How might we make Synthsrch resilient and professional so a solo researcher never hits a dead search or a toy chat when keys, limits, or models change?

## Recommended Direction

Keep V1's local-first core (FastAPI + Vite static + SQLite, search-only providers, local trafilatura/crawl4ai extract) and add four thin vertical slices: (1) silent sequential search fallback — requested provider first, then key-present others, `provider` echoes actual; (2) BYO-model multi-LLM via one `LLMAdapter` (OpenAI-compat covers NIM/OpenAI/OpenRouter, native Anthropic/Gemini), free-text model ID, no curated list; (3) hidden NotebookLM-style system prompt + `react-markdown/GFM` chat with 280px session side-panel replacing History; (4) sources drawer (current / last-search / new-search + paste URL) backed by `PATCH /sessions/{id}/sources` with auto re-extract.

Why this: cheapest reliability win (no parallel billing), fastest LLM breadth (one compat path + two natives), pro feel without redesign (markdown + sidebar), grounding stays truthful (gap-fill + immediate context update on remove).

## Key Assumptions to Validate

- [ ] Silent fallback won't hide broken keys — check via Settings `keys_present` + server log spot-check
- [ ] One OpenAI-compat client truly covers NIM/OpenAI/OpenRouter streaming — mocked + one live call each
- [ ] `react-markdown + rehype-sanitize` blocks model HTML injection — malicious-markdown test
- [ ] 10-source / 6k-char cap still fits all five LLMs' context — measure prompt length per provider

## MVP Scope

In: router fallback, 5-LLM adapters + keys + free-text model, prompt v2, markdown + sidebar + session APIs, sources drawer, tests + E2E.
Out: parallel search race, curated model catalog, search-history UI beyond sidebar, knowledge-graph revival, cloud sync.

## Not Doing (and Why)

- Parallel provider race — doubles cost per search for marginal latency.
- Model catalog/datalist — user types IDs; catalog rots monthly.
- Separate History page — sidebar resumes faster; keeps one chat home.
- Provider extract/scrape APIs — V1 local-only rule stands (privacy + cost).

## Open Questions

- Sidebar: sessions-only or also searches tab? (default sessions-only for v2)
- Session rename: auto-from-topic or manual? (default manual inline edit)
- Fallback order: fixed stable order vs user drag-order? (v2 fixed; reorder later if asked)

# ADR-001: Silent auto-routers for search and LLM providers

## Status
Accepted

## Date
2026-10-15

## Context
V1 required the user to pick one search provider per search and used NVIDIA
NIM exclusively for chat. A rate limit, an expired key, or a provider outage
meant a dead end: `MISSING_KEY` / `PROVIDER_ERROR` with manual recovery.
V2 adds four more LLM providers (OpenAI, Anthropic, Gemini, OpenRouter), so
per-provider failures become routine rather than exceptional.

## Decision
- **Search:** sequential try-next over key-configured providers (requested
  first, or `auto` order), one provider billed per search, never parallel.
  The response echoes the provider actually used; failures are silent in the
  UI and logged server-side.
- **LLM:** `LLMAdapter` per provider (OpenAI-compatible client covers
  NIM/OpenAI/OpenRouter; native HTTPS for Anthropic/Gemini, no extra SDKs).
  The chat tries the selected `provider:model` first, then other providers
  that have both a key and a configured model. Pre-token failures fall
  through; once a provider yields a token the call is committed to it.
- **Transparency, not silence, for chat:** every LLM switch emits a `notice`
  event (`X failed (reason) — switched to Y:model`), shown as a pill in the
  thread and persisted with the session. Search stays fully silent (the
  `showing` line names the provider used).

## Alternatives Considered
- **Parallel race:** fastest but bills N providers per search; rejected on cost.
- **No fallback (V1 behavior):** predictable but fragile; rejected — the
  five-provider setup exists precisely so one outage doesn't block research.
- **Mid-stream switching:** would mix two models' voices in one answer;
  rejected — commit after the first token, surface errors instead.

## Consequences
- A bad model ID for the selected provider (e.g. a NIM id sent to Gemini)
  resolves itself via fallback, with the notice explaining why.
- Server logs carry `llm fallback: X → next (…)` lines; error/notice text is
  passed through `sanitize_error()` so request URLs can never leak keys into
  chat or logs.
- Frontend parses SSE with a buffering reader (`SseBuffer`) so payloads split
  across TCP chunks are never dropped.

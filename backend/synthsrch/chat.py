"""Structured chat — deterministic JSON prompt + Groq (OpenAI-compatible)."""
from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .config import get_settings
from .providers.base import SearchResult


def build_system_prompt(topic: str, purpose: str, domain_keywords: list[str], n_sources: int) -> str:
    kws = ", ".join(domain_keywords) if domain_keywords else "(none)"
    refs = ", ".join(f"[S{i+1}]" for i in range(n_sources)) if n_sources else "(no sources)"
    return (
        "You are Synthsrch synthesiser. Learn without clutter.\n"
        f"Topic: {topic}\nPurpose: {purpose}\nDomainKeywords: {kws}\n"
        f"Sources: {refs}\n"
        "Rules: Ground EVERY factual claim in the provided excerpts and cite like [S1]. "
        "If sources disagree, say which source says what. "
        "If evidence is insufficient, say so explicitly. Be concise and structured."
    )


def build_user_prompt(query: str, sources: list[SearchResult], extracts: dict[str, str], max_chars: int = 6000) -> str:
    parts = [f"Query: {query}\n"]
    for i, s in enumerate(sources):
        tag = f"S{i+1}"
        body = (extracts.get(s.id) or s.snippet or "")[:max_chars]
        parts.append(f"[{tag}] {s.title}\nURL: {s.url}\nPublisher: {s.publisher}\n{body}\n")
    return "\n".join(parts)


def groq_client() -> AsyncOpenAI:
    s = get_settings()
    if not s.groq_api_key:
        raise PermissionError("groq: missing API key — add a Groq key in Settings.")
    # Bounded waits: a stalled provider must surface as an error, never a silent hang.
    return AsyncOpenAI(base_url=s.groq_base_url, api_key=s.groq_api_key, timeout=120.0, max_retries=1)


async def stream_chat(
    model: str, system: str, user: str, max_tokens: int = 4096
) -> AsyncIterator[tuple[str, str]]:
    """Yields ("content"|"reasoning", text) deltas.

    Reasoning models (e.g. gpt-oss, qwq) think for many seconds before the first
    answer token; forwarding their thinking keeps the UI alive instead of showing
    a dead spinner.
    """
    client = groq_client()
    stream = await client.chat.completions.create(
        model=model or get_settings().groq_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        try:
            delta = chunk.choices[0].delta
            content = delta.content or ""
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None) or ""
        except Exception:
            continue
        if content:
            yield ("content", content)
        if reasoning:
            yield ("reasoning", reasoning if isinstance(reasoning, str) else str(reasoning))


async def complete_chat(model: str, system: str, user: str, max_tokens: int = 4096) -> str:
    parts: list[str] = []
    async for kind, text in stream_chat(model, system, user, max_tokens):
        if kind == "content":
            parts.append(text)
    return "".join(parts)

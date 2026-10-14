"""Structured chat — deterministic JSON prompt + NVIDIA NIM (OpenAI-compatible)."""
from __future__ import annotations

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


def nim_client() -> AsyncOpenAI:
    s = get_settings()
    if not s.nim_api_key:
        raise PermissionError("nim: missing API key — add NVIDIA_API_KEY in Settings.")
    return AsyncOpenAI(base_url=s.nim_base_url, api_key=s.nim_api_key)


async def stream_chat(model: str, system: str, user: str, max_tokens: int = 1024):
    client = nim_client()
    stream = await client.chat.completions.create(
        model=model or get_settings().nim_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content or ""
        except Exception:
            delta = ""
        if delta:
            yield delta


async def complete_chat(model: str, system: str, user: str, max_tokens: int = 1024) -> str:
    parts: list[str] = []
    async for d in stream_chat(model, system, user, max_tokens):
        parts.append(d)
    return "".join(parts)

"""Multi-LLM dispatch (V2) — one normalized stream for 5 providers."""
from __future__ import annotations

from collections.abc import AsyncIterator

LLM_PROVIDERS = ("nim", "openai", "anthropic", "gemini", "openrouter")


def parse_ref(ref: str, default_provider: str, default_model: str) -> tuple[str, str]:
    """Split 'provider:model' or plain model ID. Empty ref → defaults."""
    ref = (ref or "").strip()
    if not ref:
        return default_provider, default_model
    if ":" in ref:
        head, tail = ref.split(":", 1)
        if head.strip().lower() in LLM_PROVIDERS and tail.strip():
            return head.strip().lower(), tail.strip()
    return default_provider, ref


def resolve_ref(provider: str | None, model: str | None) -> tuple[str, str]:
    from ..config import get_settings

    s = get_settings()
    prov = (provider or s.llm_provider or "nim").lower()
    if prov not in LLM_PROVIDERS:
        raise ValueError(f"unknown LLM provider '{provider}'. Choose one of: {', '.join(LLM_PROVIDERS)}")
    mod = (model or s.llm_model or s.nim_model or "").strip()
    if not mod:
        raise PermissionError(f"{prov}: no model configured — type a model ID in chat or Settings.")
    if ":" in mod:
        head, tail = mod.split(":", 1)
        if head.strip().lower() in LLM_PROVIDERS and tail.strip():
            return head.strip().lower(), tail.strip()
    return prov, mod


async def stream_llm(
    provider: str, model: str, system: str, user: str, max_tokens: int = 4096
) -> AsyncIterator[tuple[str, str]]:
    prov = (provider or "").lower()
    if prov in ("nim", "openai", "openrouter"):
        async for kind, text in _openai_compat_stream(prov, model, system, user, max_tokens):
            yield kind, text
    elif prov == "anthropic":
        from .anthropic import stream_anthropic

        async for kind, text in stream_anthropic(model, system, user, max_tokens):
            yield kind, text
    elif prov == "gemini":
        from .gemini import stream_gemini

        async for kind, text in stream_gemini(model, system, user, max_tokens):
            yield kind, text
    else:
        raise ValueError(f"unknown LLM provider '{provider}'. Choose one of: {', '.join(LLM_PROVIDERS)}")


async def _openai_compat_stream(
    provider: str, model: str, system: str, user: str, max_tokens: int = 4096
) -> AsyncIterator[tuple[str, str]]:
    from .openai_compat import stream_openai_compat

    async for kind, text in stream_openai_compat(provider, model, system, user, max_tokens):
        yield kind, text


_KEY_ATTRS = {
    "nim": "nim_api_key",
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "gemini": "gemini_api_key",
    "openrouter": "openrouter_api_key",
}

_MODEL_ATTRS = {
    "nim": "nim_model",
    "openai": "openai_model",
    "anthropic": "anthropic_model",
    "gemini": "gemini_model",
    "openrouter": "openrouter_model",
}


def provider_has_key(provider: str) -> bool:
    from ..config import get_settings

    attr = _KEY_ATTRS.get(provider, "")
    return bool(getattr(get_settings(), attr, "") or "")


def model_for(provider: str) -> str:
    """Configured model for a provider: per-provider field, else generic fallback."""
    from ..config import get_settings

    s = get_settings()
    specific = (getattr(s, _MODEL_ATTRS.get(provider, ""), "") or "").strip()
    if specific:
        return specific
    return (s.llm_model or "").strip()


def fallback_chain(preferred_provider: str, preferred_model: str) -> list[tuple[str, str]]:
    """Ordered (provider, model) attempts: preferred first, then keyed others.

    A provider joins the chain only with both an API key and a model name
    (per-provider model or the generic llm_model fallback). Silent like search.
    """
    order = [preferred_provider] + [p for p in LLM_PROVIDERS if p != preferred_provider]
    chain: list[tuple[str, str]] = []
    for i, prov in enumerate(order):
        if i == 0:
            if preferred_model.strip() and provider_has_key(prov):
                chain.append((prov, preferred_model.strip()))
        else:
            mod = model_for(prov)
            if mod and provider_has_key(prov):
                chain.append((prov, mod))
    return chain

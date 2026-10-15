"""Multi-LLM adapters (V2) — parse + dispatch."""
from synthsrch.llm.base import LLM_PROVIDERS, parse_ref


def test_providers_known():
    assert set(LLM_PROVIDERS) == {"nim", "openai", "anthropic", "gemini", "openrouter"}


def test_parse_ref_with_prefix():
    p, m = parse_ref("openrouter:anthropic/claude-sonnet-4", "nim", "default-m")
    assert p == "openrouter" and m == "anthropic/claude-sonnet-4"


def test_parse_ref_plain_uses_default_provider():
    p, m = parse_ref("gpt-4o-mini", "openai", "default-m")
    assert p == "openai" and m == "gpt-4o-mini"


def test_parse_ref_empty_uses_defaults():
    p, m = parse_ref("", "nim", "nvidia/nemotron-3.5-lightning-30b-a3b")
    assert p == "nim" and "nemotron" in m


async def test_dispatch_openai_compat(monkeypatch):
    import synthsrch.llm.base as b

    seen = {}

    async def fake_stream(provider, model, system, user, max_tokens=4096):
        seen.update(provider=provider, model=model)
        yield ("content", "hi")

    monkeypatch.setattr(b, "_openai_compat_stream", fake_stream)
    out = []
    async for kind, text in b.stream_llm("openai", "gpt-4o-mini", "sys", "usr"):
        out.append((kind, text))
    assert out == [("content", "hi")]
    assert seen["provider"] == "openai"


async def test_dispatch_unknown_provider_errors():
    import synthsrch.llm.base as b
    import pytest

    with pytest.raises(ValueError):
        async for _ in b.stream_llm("nope", "m", "s", "u"):
            pass

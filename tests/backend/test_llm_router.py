"""LLM auto-router: preferred first, silent fallback to keyed providers."""
import pytest

import synthsrch.chat as chatmod


def _keys(monkeypatch, **kw):
    import synthsrch.config as cfg

    s = cfg.get_settings()
    for k, v in kw.items():
        setattr(s, k, v)


async def test_llm_falls_through_to_next_keyed_provider(monkeypatch):
    import synthsrch.config as cfg

    _keys(monkeypatch,
          openai_api_key="sk-test", openai_model="gpt-4o-mini",
          gemini_api_key="g-test", gemini_model="gemini-2.0-flash")

    async def fake_stream(provider, model, system, user, max_tokens=4096):
        if provider == "openai":
            raise RuntimeError("openai: provider error 429 — check key/credits.")
        yield ("content", f"from-{provider}:{model}")

    import synthsrch.llm as llmpkg
    import synthsrch.llm.base as base

    monkeypatch.setattr(llmpkg, "stream_llm", fake_stream)
    monkeypatch.setattr(base, "stream_llm", fake_stream)

    out = [(k, t) async for k, t in chatmod.stream_chat_llm("openai", "gpt-4o-mini", "s", "u")]
    assert out[0][0] == "notice" and "openai" in out[0][1] and "gemini" in out[0][1]
    assert out[-1] == ("content", "from-gemini:gemini-2.0-flash")
    _keys(monkeypatch, openai_api_key="", gemini_api_key="")


async def test_llm_all_fail_raises_combined(monkeypatch):
    _keys(monkeypatch,
          openai_api_key="sk-test", openai_model="gpt-4o-mini",
          gemini_api_key="g-test", gemini_model="gemini-2.0-flash")

    async def always_fail(provider, model, system, user, max_tokens=4096):
        raise RuntimeError(f"{provider}: provider error 500")
        yield ("content", "unreachable")  # noqa: unreachable — keeps generator type

    import synthsrch.llm as llmpkg
    import synthsrch.llm.base as base

    monkeypatch.setattr(llmpkg, "stream_llm", always_fail)
    monkeypatch.setattr(base, "stream_llm", always_fail)

    with pytest.raises(RuntimeError, match="openai|gemini"):
        async for _ in chatmod.stream_chat_llm("openai", "gpt-4o-mini", "s", "u"):
            pass
    _keys(monkeypatch, openai_api_key="", gemini_api_key="")

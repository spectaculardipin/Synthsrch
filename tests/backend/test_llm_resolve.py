"""Regression: resolve_ref must import app config (not synthsrch.llm.config)."""
from synthsrch.llm.base import resolve_ref


def test_resolve_ref_gemini_and_defaults():
    assert resolve_ref("gemini", "gemini-2.0-flash") == ("gemini", "gemini-2.0-flash")
    prov, mod = resolve_ref(None, None)
    assert prov in ("nim", "openai", "anthropic", "gemini", "openrouter")
    assert mod != ""


async def test_stream_chat_llm_resolves_without_import_error(monkeypatch):
    import synthsrch.chat as chatmod

    async def fake_llm(provider, model, system, user, max_tokens=4096):
        assert provider == "gemini" and model == "gemini-2.0-flash"
        yield ("content", "ok")

    import synthsrch.llm as llmpkg

    monkeypatch.setattr(llmpkg, "stream_llm", fake_llm)
    monkeypatch.setattr("synthsrch.llm.base.stream_llm", fake_llm)
    out = [(k, t) async for k, t in chatmod.stream_chat_llm("gemini", "gemini-2.0-flash", "s", "u")]
    assert out == [("content", "ok")]

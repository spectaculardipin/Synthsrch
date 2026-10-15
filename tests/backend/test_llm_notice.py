"""Router switch must emit a notice (reason + next model), not fail silently."""
import synthsrch.chat as chatmod
from synthsrch.chat import sanitize_error


def test_sanitize_error_strips_keys():
    dirty = "Server error '503' for url 'https://x.test/m?alt=sse&key=SECRET123' (api_key=ABC)"
    clean = sanitize_error(dirty)
    assert "SECRET123" not in clean and "ABC" not in clean
    assert "key=[REDACTED]" in clean and "503" in clean


async def test_fallback_emits_notice_with_reason_and_next_model(monkeypatch):
    import synthsrch.config as cfg

    s = cfg.get_settings()
    s.openai_api_key = "sk-test"
    s.openai_model = "gpt-4o-mini"
    s.gemini_api_key = "g-test"
    s.gemini_model = "gemini-2.0-flash"
    try:
        async def fake_stream(provider, model, system, user, max_tokens=4096):
            if provider == "openai":
                raise RuntimeError("openai: provider error 429 for url 'https://x.test/?key=SECRET123' — check key/credits.")
            yield ("content", "answered-by-gemini")

        import synthsrch.llm as llmpkg
        import synthsrch.llm.base as base

        monkeypatch.setattr(llmpkg, "stream_llm", fake_stream)
        monkeypatch.setattr(base, "stream_llm", fake_stream)

        out = [(k, t) async for k, t in chatmod.stream_chat_llm("openai", "gpt-4o-mini", "s", "u")]
        kinds = [k for k, _ in out]
        assert kinds[0] == "notice"
        notice = out[0][1]
        assert "openai" in notice and "429" in notice and "gemini" in notice and "gemini-2.0-flash" in notice
        assert "SECRET123" not in notice and "[REDACTED]" in notice
        assert ("content", "answered-by-gemini") in out
    finally:
        s.openai_api_key = ""
        s.gemini_api_key = ""

"""A stream that dies mid-response must surface an error event, never silence."""
from fastapi.testclient import TestClient

import synthsrch.app as appmod
from synthsrch import config as cfg
from synthsrch.app import app


def _isolate(tmp_path):
    cfg.get_settings.cache_clear()
    s = cfg.get_settings()
    s.data_dir = tmp_path / "data"
    s.db_path = tmp_path / "data" / "t.db"
    s.data_dir.mkdir(parents=True, exist_ok=True)
    import synthsrch.db as dbmod
    dbmod._engine = None
    dbmod._SessionFactory = None


def test_midstream_failure_yields_error_event_and_saves_partial(tmp_path, monkeypatch):
    _isolate(tmp_path)

    async def dying_stream(provider, model, system, user, max_tokens=4096):
        yield ("content", "partial-answer-")
        raise RuntimeError("gemini: provider error 500 — backend crash")

    monkeypatch.setattr(appmod, "stream_chat_llm", dying_stream)
    with TestClient(app) as c:
        sid = c.post("/api/sessions", json={"topic": "t", "purpose": "p"}).json()["session_id"]
        events = [ln[6:] for ln in c.post(f"/api/sessions/{sid}/chat", json={"query": "q?"}).iter_lines()
                  if ln.startswith("data: ")]
        assert "[DONE]" in events
        assert any("error" in e and "gemini" in e for e in events), events
        det = c.get(f"/api/sessions/{sid}").json()
        roles = [m["role"] for m in det["messages"]]
        assert roles == ["user", "assistant"]
        assert det["messages"][1]["content"].startswith("partial-answer-")

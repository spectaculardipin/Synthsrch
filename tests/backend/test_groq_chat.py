"""Groq provider: bounded client, reasoning+content stream protocol, chat persistence."""
from fastapi.testclient import TestClient

import synthsrch.app as appmod
import synthsrch.chat as chatmod
from synthsrch import config as cfg
from synthsrch.app import app


def _isolate(tmp_path):
    cfg.get_settings.cache_clear()
    s = cfg.get_settings()
    s.data_dir = tmp_path / "data"
    s.db_path = tmp_path / "data" / "t.db"
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.groq_api_key = "gsk-test"
    import synthsrch.db as dbmod
    dbmod._engine = None
    dbmod._SessionFactory = None


def test_groq_client_is_bounded(tmp_path):
    _isolate(tmp_path)
    c = chatmod.groq_client()
    assert float(c.timeout) == 120.0
    assert c.max_retries == 1
    assert "groq.com" in str(c.base_url)


def test_groq_client_needs_key(tmp_path):
    _isolate(tmp_path)
    cfg.get_settings().groq_api_key = ""
    try:
        chatmod.groq_client()
    except PermissionError as e:
        assert "Groq" in str(e)
    else:
        raise AssertionError("expected PermissionError")


def test_stream_forwards_reasoning_and_content(tmp_path, monkeypatch):
    _isolate(tmp_path)

    class Delta:
        def __init__(self, content=None, reasoning_content=None, reasoning=None):
            self.content = content
            self.reasoning_content = reasoning_content
            self.reasoning = reasoning

    class Choice:
        def __init__(self, delta):
            self.delta = delta

    class Chunk:
        def __init__(self, **kw):
            self.choices = [Choice(Delta(**kw))]

    async def fake_create(**kw):
        assert kw["model"] == "llama-3.1-8b-instant"
        assert kw["stream"] is True

        async def gen():
            yield Chunk(reasoning_content="thinking…")
            yield Chunk(content="Hello")
            yield Chunk(content=" world")

        return gen()

    class FakeCompletions:
        create = staticmethod(fake_create)

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(chatmod, "groq_client", lambda: FakeClient())
    import asyncio

    async def collect():
        return [(k, t) async for k, t in chatmod.stream_chat("llama-3.1-8b-instant", "s", "u")]

    out = asyncio.run(collect())
    assert out == [("reasoning", "thinking…"), ("content", "Hello"), ("content", " world")]
    assert asyncio.run(chatmod.complete_chat("llama-3.1-8b-instant", "s", "u")) == "Hello world"


def test_chat_persists_user_message(tmp_path, monkeypatch):
    _isolate(tmp_path)

    async def fake_stream(model, system, user, max_tokens=4096):
        yield ("content", "Hi.")

    monkeypatch.setattr(appmod, "stream_chat", fake_stream)
    with TestClient(app) as c:
        sid = c.post("/api/sessions", json={"topic": "t", "purpose": "p"}).json()["session_id"]
        body = []
        r = c.post(f"/api/sessions/{sid}/chat", json={"query": "hello"})
        for line in r.iter_lines():
            if line.startswith("data: "):
                body.append(line[6:])
        assert "[DONE]" in body
        import asyncio
        from synthsrch.models import Message
        from sqlalchemy import select

        async def roles():
            import synthsrch.db as dbmod
            async with dbmod.session_factory()() as db:
                rows = (await db.execute(select(Message).where(Message.session_id == sid))).scalars().all()
                return sorted(x.role for x in rows)

        assert asyncio.run(roles()) == ["assistant", "user"]

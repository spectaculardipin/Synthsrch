"""Chat carries full excerpts: background pre-extract persists rows, and the chat
endpoint gap-fills any source still missing text at send time."""

from fastapi.testclient import TestClient

import synthsrch.app as appmod
from synthsrch import config as cfg
from synthsrch.app import app
from synthsrch.models import ResultCache, Search


def _isolate(tmp_path):
    cfg.get_settings.cache_clear()
    s = cfg.get_settings()
    s.data_dir = tmp_path / "data"
    s.db_path = tmp_path / "data" / "t.db"
    s.data_dir.mkdir(parents=True, exist_ok=True)
    import synthsrch.db as dbmod
    dbmod._engine = None
    dbmod._SessionFactory = None


def _seed_search():
    import asyncio
    import synthsrch.db as dbmod

    async def go():
        await dbmod.init_db()
        async with dbmod.session_factory()() as db:
            db.add(Search(id="srch-1", query="q", provider="exa", count=2,
                          rank_start=1, rank_end=2, keywords="[]",
                          keyword_mode="ANY", subtopics="[]"))
            db.add(ResultCache(id="exa-1", search_id="srch-1", rank=1, title="T1",
                               url="https://example.com/1", publisher="example.com",
                               snippet="short snip", score=None))
            await db.commit()

    asyncio.run(go())


def test_chat_gap_fills_missing_extracts(tmp_path, monkeypatch):
    _isolate(tmp_path)
    _seed_search()
    seen = {}

    async def fake_stream(provider, model, system, user, max_tokens=4096):
        seen["user"] = user
        yield ("content", "Answer.")

    async def fake_gap_fill(pairs):
        assert pairs == [("exa-1", "https://example.com/1")]
        return [("exa-1", "FULL EXTRACTED BODY", "trafilatura")]

    monkeypatch.setattr(appmod, "stream_chat_llm", fake_stream)
    monkeypatch.setattr(appmod, "_gap_fill_extracts", fake_gap_fill)
    with TestClient(app) as c:
        sid = c.post("/api/sessions",
                     json={"topic": "t", "purpose": "p", "sourceIds": ["exa-1"]}).json()["session_id"]
        lines = c.post(f"/api/sessions/{sid}/chat", json={"query": "q?"}).iter_lines()
        assert "[DONE]" in [ln[6:] for ln in lines if ln.startswith("data: ")]
    assert "FULL EXTRACTED BODY" in seen["user"]
    assert "[S1]" in seen["user"]

    import asyncio

    async def check():
        import synthsrch.db as dbmod
        async with dbmod.session_factory()() as db:
            row = await db.get(ResultCache, "exa-1")
            return row.extract_text, row.extract_via

    text, via = asyncio.run(check())
    assert text == "FULL EXTRACTED BODY"[: cfg.get_settings().extract_max_chars]
    assert via == "trafilatura"


def test_chat_skips_gap_fill_when_cached(tmp_path, monkeypatch):
    _isolate(tmp_path)
    _seed_search()
    called = []

    async def fake_stream(provider, model, system, user, max_tokens=4096):
        yield ("content", "Answer.")

    async def fake_gap_fill(pairs):
        called.append(pairs)
        return []

    async def fake_extract(self, url, max_chars=None, allow_fallback=True):
        return ("CACHED VIA ENDPOINT", "trafilatura")

    from synthsrch import extract as exmod
    monkeypatch.setattr(appmod, "stream_chat_llm", fake_stream)
    monkeypatch.setattr(appmod, "_gap_fill_extracts", fake_gap_fill)
    monkeypatch.setattr(exmod.LocalExtractor, "extract", fake_extract)
    with TestClient(app) as c:
        # background pre-extract path: /api/extract persists the row
        r = c.post("/api/extract", json={"url": "https://example.com/1", "result_id": "exa-1"})
        assert r.status_code == 200
        sid = c.post("/api/sessions",
                     json={"topic": "t", "purpose": "p", "sourceIds": ["exa-1"]}).json()["session_id"]
        c.post(f"/api/sessions/{sid}/chat", json={"query": "q?"})
    assert called == []  # nothing missing → gap fill never runs

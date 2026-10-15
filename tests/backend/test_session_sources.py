"""Session list/detail + sources PATCH (V2)."""
import json

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


def _seed_result(rid="exa-1", url="https://example.com/1"):
    import asyncio
    import synthsrch.db as dbmod

    async def go():
        await dbmod.init_db()
        async with dbmod.session_factory()() as db:
            db.add(Search(id="srch-1", query="q", provider="exa", count=2,
                          rank_start=1, rank_end=2, keywords="[]",
                          keyword_mode="ANY", subtopics="[]"))
            db.add(ResultCache(id=rid, search_id="srch-1", rank=1, title="T1",
                               url=url, publisher="example.com",
                               snippet="snip", score=None,
                               extract_text="CACHED BODY", extract_via="trafilatura"))
            await db.commit()

    asyncio.run(go())


def test_session_crud_and_sources_patch(tmp_path, monkeypatch):
    _isolate(tmp_path)
    _seed_result()

    async def fake_extract(self, url, max_chars=None, allow_fallback=True):
        return ("EXTRACTED " + url, "trafilatura")

    from synthsrch import extract as exmod
    monkeypatch.setattr(exmod.LocalExtractor, "extract", fake_extract)

    with TestClient(app) as c:
        sid = c.post("/api/sessions",
                     json={"topic": "t", "purpose": "p", "sourceIds": ["exa-1"],
                           "provider": "nim", "model": "m1"}).json()["session_id"]
        # list
        lst = c.get("/api/sessions").json()
        assert any(s["id"] == sid for s in lst["sessions"])
        # detail includes messages (empty) + sources
        det = c.get(f"/api/sessions/{sid}").json()
        assert det["topic"] == "t" and det["sourceIds"] == ["exa-1"]
        assert det["messages"] == []
        # chat once to create messages
        async def fake_stream(provider, model, system, user, max_tokens=4096):
            yield ("content", "Hi.")

        monkeypatch.setattr(appmod, "stream_chat_llm", fake_stream)
        c.post(f"/api/sessions/{sid}/chat", json={"query": "hello"})
        det2 = c.get(f"/api/sessions/{sid}").json()
        assert [m["role"] for m in det2["messages"]] == ["user", "assistant"]
        # add pasted URL + remove existing
        r = c.patch(f"/api/sessions/{sid}/sources",
                    json={"add": [{"url": "https://example.com/pasted"}], "remove": ["exa-1"]})
        assert r.status_code == 200
        assert "exa-1" not in r.json()["sourceIds"]
        assert len(r.json()["sourceIds"]) == 1
        # delete
        assert c.delete(f"/api/sessions/{sid}").status_code == 200
        assert c.get(f"/api/sessions/{sid}").status_code == 404

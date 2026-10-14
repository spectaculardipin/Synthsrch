"""Regression: repeat/overlapping searches must not 500 on cache PK; extracts survive refresh."""
import synthsrch.app as appmod
from fastapi.testclient import TestClient
from synthsrch.app import app
from synthsrch.providers.base import SearchResult


def _rows(query: str, **kw):
    base = {"publisher": "example.com", "rank": 1, "score": 0.9, "snippet": "snip"}
    base.update(kw)
    return [
        SearchResult(id="tavily-aaa", title="A", url="https://example.com/a", **base),
        SearchResult(id="tavily-bbb", title="B", url="https://example.com/b", **base),
    ]


def test_repeat_search_upserts_without_500(tmp_path, monkeypatch):
    from synthsrch import config as cfg
    cfg.get_settings.cache_clear()
    s = cfg.get_settings()
    s.data_dir = tmp_path / "data"
    s.db_path = tmp_path / "data" / "t.db"
    s.data_dir.mkdir(parents=True, exist_ok=True)
    import synthsrch.db as dbmod
    dbmod._engine = None
    dbmod._SessionFactory = None

    async def fake_run(req):
        return _rows(req.query), "tavily"

    monkeypatch.setattr(appmod, "run_search", fake_run)
    with TestClient(app) as c:
        r1 = c.post("/api/search", json={"query": "q", "provider": "tavily"})
        assert r1.status_code == 200, r1.text
        id1 = r1.json()["search_id"]
        # seed an extraction on the first row, then re-search: upsert must keep it
        from sqlalchemy import select
        import asyncio

        async def seed():
            async with dbmod.session_factory()() as db:
                row = await db.get(dbmod.__dict__.get("ResultCache", None) or __import__("synthsrch.models", fromlist=["ResultCache"]).ResultCache, "tavily-aaa")
                row.extract_text = "CACHED TEXT"
                row.extract_via = "trafilatura"
                await db.commit()

        asyncio.run(seed())

        r2 = c.post("/api/search", json={"query": "q", "provider": "tavily"})
        assert r2.status_code == 200, r2.text
        assert r2.json()["search_id"] != id1

        async def check():
            from synthsrch.models import ResultCache
            async with dbmod.session_factory()() as db:
                rows = (await db.execute(select(ResultCache))).scalars().all()
                by_id = {x.id: x for x in rows}
                assert len(rows) == 2, f"expected upsert, got {len(rows)} rows"
                assert by_id["tavily-aaa"].extract_text == "CACHED TEXT"

        asyncio.run(check())

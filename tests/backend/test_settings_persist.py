"""Regression: settings persist across restart; blank PUT can't wipe keys."""
from fastapi.testclient import TestClient

from synthsrch import config as cfg
from synthsrch.app import app, hydrate_settings_from_db


def _fresh_client(tmp_path, monkeypatch):
    # Isolate by pointing the cached Settings at a tmp DB (field defaults are
    # per-instance; mutating env post-import does NOT relocate the DB).
    from synthsrch import config as cfg
    cfg.get_settings.cache_clear()
    s = cfg.get_settings()
    s.data_dir = tmp_path / "data"
    s.db_path = tmp_path / "data" / "t.db"
    s.data_dir.mkdir(parents=True, exist_ok=True)
    import synthsrch.db as dbmod
    dbmod._engine = None
    dbmod._SessionFactory = None
    c = TestClient(app)
    with TestClient(app):
        pass
    return c


def test_put_persists_and_hydrates_after_restart(tmp_path, monkeypatch):
    c = _fresh_client(tmp_path, monkeypatch)
    r = c.put("/api/settings", json={"tavily_api_key": "tvly-testkey123", "nim_model": "meta/llama-3.1-70b-instruct"})
    assert r.status_code == 200
    body = r.json()
    assert body["keys_present"]["tavily"] is True  # PUT echoes state
    assert body["nim_model"] == "meta/llama-3.1-70b-instruct"

    # Simulate restart: drop cached Settings + engine, re-hydrate from DB file.
    cfg.get_settings.cache_clear()
    s2 = cfg.get_settings()
    s2.data_dir = tmp_path / "data"
    s2.db_path = tmp_path / "data" / "t.db"
    import synthsrch.db as dbmod
    dbmod._engine = None
    dbmod._SessionFactory = None
    import asyncio
    asyncio.run(hydrate_settings_from_db())
    assert cfg.get_settings().tavily_api_key == "tvly-testkey123"

    c2 = TestClient(app)
    assert c2.get("/api/settings").json()["keys_present"]["tavily"] is True


def test_blank_put_does_not_wipe_key(tmp_path, monkeypatch):
    c = _fresh_client(tmp_path, monkeypatch)
    c.put("/api/settings", json={"exa_api_key": "exa-goodkey"})
    r = c.put("/api/settings", json={"exa_api_key": "   "})
    assert r.status_code == 200
    assert r.json()["keys_present"]["exa"] is True
    assert cfg.get_settings().exa_api_key == "exa-goodkey"

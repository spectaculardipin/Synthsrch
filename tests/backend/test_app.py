from fastapi.testclient import TestClient

from synthsrch.app import app


def test_health_and_models(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True
    m = c.get("/api/models")
    assert "models" in m.json()

"""SSRF + input-cap guards: hostile URLs never reach the network."""
import pytest

from synthsrch.extract import assert_public_url


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://127.0.0.1:8765/api/health",
    "http://[::1]/",
    "http://10.0.0.1/",
    "http://172.16.5.4/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://0.0.0.0/",
    "http://localhost/",
    "http://localhost:8765/",
    "http://LOCALHOST/",
    "http://foo.localhost/",
    "ftp://example.com/x",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "data:text/plain,hi",
    "",
    "not-a-url",
    "http://",
])
def test_blocked_without_network(url):
    with pytest.raises(ValueError, match="extract blocked"):
        assert_public_url(url)


def test_public_literal_ip_passes_without_dns():
    assert assert_public_url("http://93.184.216.34/") == "http://93.184.216.34/"


def test_public_hostname_passes_with_mocked_dns(monkeypatch):
    import socket
    real = socket.getaddrinfo
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))])
    assert assert_public_url("https://example.com/x") == "https://example.com/x"
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("nxdomain")))
    with pytest.raises(ValueError, match="DNS"):
        assert_public_url("https://nonexistent.invalid/")
    _ = real


def test_hostname_resolving_private_is_blocked(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("10.1.2.3", 0)),
                                         (2, 1, 6, "", ("93.184.216.34", 0))])
    with pytest.raises(ValueError, match="non-public"):
        assert_public_url("https://evil.example/")


def test_input_caps_rejected_with_422():
    from fastapi.testclient import TestClient
    from synthsrch.app import app
    c = TestClient(app)
    r = c.post("/api/sessions/sess-x/chat", json={"query": "q" * 4001})
    assert r.status_code in (404, 422)  # 404 unknown session or 422 too long
    r = c.post("/api/sessions/sess-x/chat", json={"query": "q" * 5000})
    assert r.status_code == 422
    r = c.post("/api/extract", json={"url": "https://example.com/" + "a" * 2048})
    assert r.status_code == 422
    r = c.put("/api/settings", json={"nim_model": "m" * 201})
    assert r.status_code == 422
    r = c.post("/api/search", json={"query": "q", "provider": "exa",
                                    "keywords": ["k"] * 21})
    assert r.status_code == 422
    r = c.post("/api/sessions/sess-x/chat", json={"query": "q", "max_tokens": 999999})
    assert r.status_code == 422

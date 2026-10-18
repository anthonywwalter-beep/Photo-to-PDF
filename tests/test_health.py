from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_index_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "Photo to Table" in r.text

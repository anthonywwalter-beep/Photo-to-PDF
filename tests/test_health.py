from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_modes():
    assert TestClient(create_app(Settings())).get("/health").json() == {"ok": True, "mode": "no-key"}
    assert TestClient(create_app(Settings(demo_mode=True))).get("/health").json()["mode"] == "demo"
    assert TestClient(create_app(Settings(api_key="k"))).get("/health").json()["mode"] == "live"


def test_index_page():
    r = TestClient(create_app(Settings())).get("/")
    assert r.status_code == 200
    assert "Photo to Table" in r.text

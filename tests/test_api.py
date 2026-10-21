from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.extraction import ExtractionError
from app.main import create_app
from app.schemas import Cell, Extraction


class RecordingExtractor:
    def __init__(self):
        self.seen = None

    def extract(self, image, media_type, layout):
        self.seen = (image, media_type, layout)
        return Extraction(layout="table", columns=["A"], rows=[[Cell(v="1", low=True)]])


class FailingExtractor:
    def extract(self, *a):
        raise ExtractionError("The reading service could not process this image. Try again in a moment.")


def post(client, data, layout=None):
    return client.post("/api/extract", params={"layout": layout} if layout else {}, content=data,
                       headers={"Content-Type": "application/octet-stream"})


def test_happy_path_returns_table_and_passes_inputs(png):
    ex = RecordingExtractor()
    r = post(TestClient(create_app(Settings(), ex)), png, layout="form")
    assert r.status_code == 200
    assert r.json() == {"layout": "table", "columns": ["A"], "rows": [[{"v": "1", "low": True}]]}
    assert ex.seen == (png, "image/png", "form")
    assert r.headers["cache-control"] == "no-store"


def test_layout_defaults_to_auto(png):
    ex = RecordingExtractor()
    post(TestClient(create_app(Settings(), ex)), png)
    assert ex.seen[2] == "auto"


def test_demo_mode_needs_no_key(png):
    c = TestClient(create_app(Settings(demo_mode=True)))
    assert post(c, png).json()["layout"] == "table"
    assert post(c, png, layout="form").json()["layout"] == "form"
    assert post(c, png, layout="list").json()["columns"] == ["Type", "Item"]


def test_no_key_and_no_demo_gives_clear_503(png):
    r = post(TestClient(create_app(Settings())), png)
    assert r.status_code == 503 and "DEMO_MODE" in r.json()["detail"]


def test_rejects_bad_uploads(png):
    c = TestClient(create_app(Settings(max_upload_bytes=len(png) - 1), RecordingExtractor()))
    assert post(c, png).status_code == 413
    c = TestClient(create_app(Settings(), RecordingExtractor()))
    assert post(c, b"").status_code == 400
    assert post(c, b"%PDF-1.7 not an image").status_code == 415
    assert post(c, png, layout="bogus").status_code == 422


def test_extractor_failure_is_502_with_safe_message(png):
    r = post(TestClient(create_app(Settings(), FailingExtractor())), png)
    assert r.status_code == 502 and "Try again" in r.json()["detail"]


def test_load_settings():
    s = load_settings({"ANTHROPIC_API_KEY": "k", "DEMO_MODE": "1", "MAX_UPLOAD_MB": "2", "EXTRACT_MODEL": "m"})
    assert (s.api_key, s.demo_mode, s.max_upload_bytes, s.model) == ("k", True, 2 * 1024 * 1024, "m")
    assert load_settings({}).demo_mode is False and load_settings({}).api_key is None


def test_size_limit_holds_without_content_length(png):
    """A chunked upload has no Content-Length header; the cap must still stop it."""
    c = TestClient(create_app(Settings(max_upload_bytes=1000), RecordingExtractor()))
    chunks = (png + b"\0" * 400 for _ in range(5))  # ~2 KB total, sent as a stream
    r = c.post("/api/extract", content=chunks)
    assert r.status_code == 413

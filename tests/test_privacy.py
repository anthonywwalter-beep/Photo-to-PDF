"""Nothing stored, nothing logged."""
import logging
import os

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import Cell, Extraction

SECRET = "SSN-123-45-6789"


class SecretExtractor:
    def extract(self, image, media_type, layout):
        return Extraction(layout="form", columns=["SSN"], rows=[[Cell(v=SECRET)]])


def snapshot(root):
    return {os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs}


def test_no_files_written_and_content_not_logged(png, tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    before = snapshot(tmp_path)
    caplog.set_level(logging.DEBUG)
    client = TestClient(create_app(Settings(), SecretExtractor()))
    r = client.post("/api/extract", content=png + SECRET.encode())
    assert r.status_code == 200 and r.json()["rows"][0][0]["v"] == SECRET
    assert snapshot(tmp_path) == before
    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert SECRET not in logged 


def test_large_upload_never_touches_disk(png, monkeypatch):
    """Regression: multipart parsers spool uploads over 1 MB to a temp file. The raw-body endpoint must not."""
    import tempfile

    rolled = []
    real = tempfile.SpooledTemporaryFile.rollover
    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", lambda self: (rolled.append(1), real(self))[1])
    big = png + b"\0" * (3 * 1024 * 1024)
    r = TestClient(create_app(Settings(), SecretExtractor())).post("/api/extract", content=big)
    assert r.status_code == 200
    assert rolled == []


def test_pdf_endpoint_stores_nothing_logs_nothing_and_drops_metadata(tmp_path, monkeypatch, caplog):
    """The PDF's title and metadata must not reach disk, the logs, or the page images sent onward."""
    import base64
    import io
    import tempfile

    from PIL import Image

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    rolled = []
    real = tempfile.SpooledTemporaryFile.rollover
    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", lambda self: (rolled.append(1), real(self))[1])
    before = snapshot(tmp_path)
    caplog.set_level(logging.DEBUG)
    img = Image.effect_noise((1400, 1800), 60).convert("RGB")      # big enough that the PDF is over 1 MB
    buf = io.BytesIO()
    img.save(buf, "PDF", title=SECRET, author=SECRET)
    pdf = buf.getvalue()
    assert len(pdf) > 1024 * 1024
    assert SECRET.encode("utf-16-be") in pdf  # Pillow stores the title as UTF-16, so the premise holds
    r = TestClient(create_app(Settings())).post("/api/pdf/pages", content=pdf)
    assert r.status_code == 200
    page = base64.b64decode(r.json()["pages"][0]["data"])
    assert SECRET.encode() not in page and SECRET.encode("utf-16-be") not in page
    assert snapshot(tmp_path) == before and rolled == []
    assert SECRET not in "\n".join(rec.getMessage() for rec in caplog.records)

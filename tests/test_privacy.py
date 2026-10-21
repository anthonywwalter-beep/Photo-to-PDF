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

"""The live smoke-test script, exercised with a fake reader (no key, no network)."""
import importlib.util
from pathlib import Path

from app.extraction import ExtractionError
from app.schemas import Cell, Extraction

SPEC = importlib.util.spec_from_file_location("smoke_live", Path(__file__).resolve().parent.parent / "scripts" / "smoke_live.py")
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class Fake:
    def __init__(self, fail=False):
        self.fail, self.seen = fail, []

    def extract(self, image, media_type, layout):
        self.seen.append((media_type, layout))
        if self.fail:
            raise ExtractionError("The reading service could not process this image. Try again in a moment.")
        return Extraction(layout="table", columns=["Name", "Time"], rows=[[Cell(v="Maria"), Cell(v="9:05", low=True)]])


def test_reports_layout_rows_and_flags(png, tmp_path, capsys):
    img = tmp_path / "a.png"
    img.write_bytes(png)
    fake = Fake()
    assert smoke.main([str(img), "--layout", "form"], extractor=fake) == 0
    out = capsys.readouterr().out
    assert "layout=table" in out and "rows=1" in out and "flagged=1" in out and "Maria | 9:05?" in out  # a trailing ? marks a flagged cell
    assert fake.seen == [("image/png", "form")]
    assert "1 of 1 images read" in out


def test_failures_set_exit_code_and_continue(png, tmp_path, capsys):
    good, bad, missing = tmp_path / "a.png", tmp_path / "b.txt", tmp_path / "nope.png"
    good.write_bytes(png)
    bad.write_bytes(b"not an image")
    assert smoke.main([str(bad), str(missing), str(good)], extractor=Fake()) == 1
    out = capsys.readouterr().out
    assert "not a JPG" in out and "cannot read file" in out and "1 of 3 images read" in out


def test_reader_error_is_reported(png, tmp_path, capsys):
    img = tmp_path / "a.png"
    img.write_bytes(png)
    assert smoke.main([str(img)], extractor=Fake(fail=True)) == 1
    assert "FAILED" in capsys.readouterr().out


def test_missing_key_gives_clear_message(png, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)                      # no .env here
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    img = tmp_path / "a.png"
    img.write_bytes(png)
    assert smoke.main([str(img)]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err

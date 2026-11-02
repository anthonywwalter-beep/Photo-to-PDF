"""The sample documents and their answer keys stay usable."""
import csv
from pathlib import Path

import pytest

from app.config import Settings
from app.extraction import sniff_media_type
from app.pdf import render_pages

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
LIMIT = Settings().max_upload_bytes
IMAGES = sorted([*SAMPLES.glob("*.png"), *SAMPLES.glob("*.jpg")])


def test_samples_exist():
    assert len(IMAGES) >= 7 and list(SAMPLES.glob("*.pdf")) and list(SAMPLES.glob("expected_*.csv"))


@pytest.mark.parametrize("path", IMAGES, ids=lambda p: p.name)
def test_each_image_is_a_real_image_under_the_size_limit(path):
    data = path.read_bytes()
    assert sniff_media_type(data) in {"image/png", "image/jpeg"}
    assert len(data) <= LIMIT


@pytest.mark.parametrize("path", sorted(SAMPLES.glob("expected_*.csv")), ids=lambda p: p.name)
def test_answer_keys_are_rectangular(path):
    rows = list(csv.reader(path.open(encoding="utf-8", newline="")))
    assert len(rows) >= 2 and all(len(r) == len(rows[0]) for r in rows)


def test_pdf_samples_convert_to_the_documented_page_counts():
    for name, pages in {"09_forms_3pages.pdf": 3, "10_signin_2pages_scan.pdf": 2}.items():
        result = render_pages((SAMPLES / name).read_bytes(), 20, LIMIT)
        assert (result.page_count, len(result.pages)) == (pages, pages), name


def test_merge_keys_match_the_documents_they_describe():
    forms = list(csv.reader((SAMPLES / "expected_03-05_intake_forms.csv").open(encoding="utf-8", newline="")))
    assert len(forms) - 1 == len(list(SAMPLES.glob("0[345]_intake_form_*")))          # one row per form image
    scan = list(csv.reader((SAMPLES / "expected_10_signin_2pages_scan.csv").open(encoding="utf-8", newline="")))
    assert len(scan) - 1 == 9                                                          # 5 rows on page 1, 4 on page 2


def test_big_photos_straddle_the_size_limit_when_generated():
    big = SAMPLES / "big"
    if not big.exists():
        pytest.skip("run `python samples/make_samples.py --big` to create them")
    assert (big / "big_photo_4mb.jpg").stat().st_size <= LIMIT < (big / "too_big_6mb.jpg").stat().st_size

"""PDF to page images: the server side of step 8. No key and no network needed."""
import base64
import io
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings, load_settings
from app.extraction import sniff_media_type
from app.main import create_app
from app.pdf import PdfError, looks_like_pdf, render_pages
from tests.conftest import ENCRYPTED_PDF


def make_pdf(n=3, size=(800, 1100), resolution=72.0, noisy=False) -> bytes:
    pages = [Image.effect_noise(size, 60).convert("RGB") if noisy else Image.new("RGB", size, (250 - 20 * i, 250, 250))
             for i in range(n)]
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:], resolution=resolution)
    return buf.getvalue()


def client(**kw):
    return TestClient(create_app(Settings(**kw)))


def post(c, data, query=""):
    return c.post("/api/pdf/pages" + query, content=data, headers={"Content-Type": "application/pdf"})


def decode(page) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(page["data"])))


def test_pages_come_back_as_jpeg_images_and_need_no_key():
    r = post(client(), make_pdf(3))  # Settings() has no key and no demo mode
    j = r.json()
    assert r.status_code == 200 and j["page_count"] == 3 and len(j["pages"]) == 3
    for p in j["pages"]:
        img = decode(p)
        assert p["media_type"] == "image/jpeg" and img.format == "JPEG"
        assert (img.width, img.height) == (p["width"], p["height"])
        assert sniff_media_type(base64.b64decode(p["data"])) == "image/jpeg"  # acceptable to /api/extract
    assert r.headers["cache-control"] == "no-store"


def test_max_parameter_and_server_page_limit():
    pdf = make_pdf(5)
    j = post(client(), pdf, "?max=2").json()
    assert j["page_count"] == 5 and len(j["pages"]) == 2
    j = post(client(max_pdf_pages=3), pdf, "?max=10").json()  # the server's own limit wins
    assert j["page_count"] == 5 and len(j["pages"]) == 3
    assert post(client(), pdf, "?max=0").status_code == 422


def test_page_size_is_bounded_whatever_the_pdf_says():
    huge = decode(post(client(), make_pdf(1, resolution=5)).json()["pages"][0])    # a page ~11520 x 15840 pt
    tiny = decode(post(client(), make_pdf(1, resolution=720)).json()["pages"][0])  # a page ~80 x 110 pt
    assert max(huge.size) == 2000
    assert max(tiny.size) <= 2000 and tiny.width == 320  # small pages are enlarged, but only up to 4x


def test_each_image_stays_under_the_image_size_limit():
    pdf = make_pdf(1, size=(1200, 1600), noisy=True)
    big = render_pages(pdf, 1, 10_000_000).pages[0]
    small = render_pages(pdf, 1, 120_000).pages[0]
    assert len(base64.b64decode(big.data)) > 120_000          # the unlimited render really is larger
    assert len(base64.b64decode(small.data)) <= 120_000       # quality and size were lowered to fit
    with pytest.raises(PdfError):
        render_pages(pdf, 1, 100)                              # cannot fit: a clear error, not a crash


def test_bad_uploads_get_clear_errors(png):
    c = client(max_pdf_bytes=2000)
    assert post(c, make_pdf(2)).status_code == 413
    c = client()
    assert post(c, b"").status_code == 400
    assert post(c, png).status_code == 415
    r = post(c, b"%PDF-1.4 this is not really a pdf")
    assert r.status_code == 422 and "damaged" in r.json()["detail"]
    r = post(c, ENCRYPTED_PDF)
    assert r.status_code == 422 and "password" in r.json()["detail"]


def test_size_limit_holds_without_content_length():
    c = client(max_pdf_bytes=1000)
    r = c.post("/api/pdf/pages", content=(b"%PDF-1.4" + b"\0" * 400 for _ in range(5)))
    assert r.status_code == 413


def test_extract_endpoint_points_pdfs_to_the_right_place():
    class Never:
        def extract(self, *a):
            raise AssertionError("a PDF must not reach the reader")

    r = TestClient(create_app(Settings(), Never())).post("/api/extract", content=make_pdf(1))
    assert r.status_code == 415 and "/api/pdf/pages" in r.json()["detail"]


def test_pdf_detection_tolerates_a_little_junk_before_the_header():
    assert looks_like_pdf(b"\n\n  %PDF-1.7 ...") and not looks_like_pdf(b"\x89PNG...") and not looks_like_pdf(b"")


def test_several_requests_at_once_all_succeed():
    pdf = make_pdf(3)
    results, barrier = [], threading.Barrier(6)

    def go():
        c = client()
        barrier.wait()
        results.append(post(c, pdf).status_code)

    with ThreadPoolExecutor(6) as pool:
        for _ in range(6):
            pool.submit(go)
    assert results == [200] * 6


def test_pdf_settings_from_environment():
    s = load_settings({"MAX_PDF_MB": "3", "MAX_PDF_PAGES": "7"})
    assert (s.max_pdf_bytes, s.max_pdf_pages) == (3 * 1024 * 1024, 7)
    d = load_settings({})
    assert (d.max_pdf_bytes, d.max_pdf_pages) == (20 * 1024 * 1024, 20)

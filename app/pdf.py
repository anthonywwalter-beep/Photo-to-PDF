"""Turn a PDF into page images. Everything happens in memory; nothing is written to disk.

The PDF is only drawn, never searched for text: the reader sees exactly the pixels the user sees,
and the new images carry none of the PDF's metadata, scripts, or attachments.
"""
from __future__ import annotations

import base64
import io
import logging
import threading

import pypdfium2 as pdfium

from .schemas import PdfPage, PdfPages

log = logging.getLogger("photo_to_table")

TARGET_LONG_SIDE = 2000  # pixels; about 170 dpi on an A4 page, enough to read small print
MAX_SCALE = 4.0          # do not blow up tiny pages (a receipt) beyond this
START_QUALITY = 85

# PDFium is generally documented as not safe to call from several threads at once. A stress test here
# (8 threads, with and without this lock) did not reproduce a crash, so the lock may not be strictly
# needed, but it costs almost nothing: a request renders at most a handful of pages.
_LOCK = threading.Lock()


class PdfError(Exception):
    """Raised with a message that is safe to show the user (never contains document text)."""


def looks_like_pdf(data: bytes) -> bool:
    return b"%PDF-" in data[:1024]  # the PDF header may be preceded by a little junk


def _jpeg(img, max_bytes: int) -> bytes:
    """Encode as JPEG, lowering quality and then size until the result fits under max_bytes."""
    quality = START_QUALITY
    for _ in range(8):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
        if quality > 40:
            quality -= 15
        else:
            img = img.resize((int(img.width * 0.75), int(img.height * 0.75)))
    raise PdfError("A page of this PDF is too detailed to convert. Try a simpler scan.")


def _render(page, max_image_bytes: int) -> PdfPage:
    try:
        width, height = page.get_size()
        if width <= 0 or height <= 0:
            raise PdfError("A page of this PDF has no size.")
        scale = min(TARGET_LONG_SIDE / max(width, height), MAX_SCALE)
        img = page.render(scale=scale).to_pil().convert("RGB")
        if max(img.size) > TARGET_LONG_SIDE:  # PDFium rounds sizes up by a pixel; keep the bound exact
            img.thumbnail((TARGET_LONG_SIDE, TARGET_LONG_SIDE))
        return PdfPage(media_type="image/jpeg", width=img.width, height=img.height,
                       data=base64.b64encode(_jpeg(img, max_image_bytes)).decode())
    finally:
        page.close()


def render_pages(data: bytes, max_pages: int, max_image_bytes: int) -> PdfPages:
    """Render up to max_pages pages. page_count says how many the PDF really has."""
    with _LOCK:
        try:
            pdf = pdfium.PdfDocument(data)
        except pdfium.PdfiumError as e:
            if getattr(e, "err_code", None) == pdfium.raw.FPDF_ERR_PASSWORD:
                raise PdfError("This PDF is password-protected. Remove the password and try again.") from None
            raise PdfError("This PDF could not be opened. It may be damaged.") from None
        try:
            total = len(pdf)
            if total == 0:
                raise PdfError("This PDF has no pages.")
            pages = [_render(pdf[i], max_image_bytes) for i in range(min(total, max_pages))]
            return PdfPages(page_count=total, pages=pages)
        except PdfError:
            raise
        except Exception as e:  # never echo the document; the class name is enough
            log.warning("pdf render failed: %s", type(e).__name__)
            raise PdfError("A page of this PDF could not be converted. It may be damaged.") from None
        finally:
            pdf.close()

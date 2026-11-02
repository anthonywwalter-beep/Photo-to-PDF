"""Web app: serves the page and the /api/extract endpoint."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .pdf import PdfError, looks_like_pdf, render_pages
from .extraction import AnthropicExtractor, DemoExtractor, ExtractionError, Extractor, sniff_media_type
from .schemas import Extraction, LayoutChoice, PdfPages

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
log = logging.getLogger("photo_to_table")


async def read_limited(request: Request, limit: int, label: str) -> bytes:
    """Read the request body into memory, stopping as soon as it passes the limit.

    Reading from the stream (not a multipart form) means no temp file is ever created.
    """
    too_big = HTTPException(413, f"{label} is too large. The limit is {limit // (1024 * 1024)} MB.")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise too_big
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > limit:
            raise too_big
    return bytes(buf)


def create_app(settings: Settings | None = None, extractor: Extractor | None = None) -> FastAPI:
    settings = settings or load_settings()
    if extractor is None:
        if settings.demo_mode:
            extractor = DemoExtractor()
        elif settings.api_key:
            extractor = AnthropicExtractor(settings.api_key, settings.model)

    # Privacy: uploads are read into memory and dropped. Nothing is written to disk,
    # and document contents are never logged (only counts and error types).
    app = FastAPI(title="Photo to Table", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "mode": "demo" if settings.demo_mode else ("live" if extractor else "no-key")}

    @app.post("/api/extract", response_model=Extraction)
    async def extract(request: Request, layout: LayoutChoice = "auto") -> Extraction:
        """Body is the raw image bytes. Read from the stream into memory, so no temp file is ever created."""
        if extractor is None:
            raise HTTPException(503, "No API key is configured. Set ANTHROPIC_API_KEY, or DEMO_MODE=1 to try sample data.")
        data = await read_limited(request, settings.max_upload_bytes, "File")
        if not data:
            raise HTTPException(400, "The file was empty.")
        media_type = sniff_media_type(data)
        if media_type is None and looks_like_pdf(data):
            raise HTTPException(415, "This is a PDF. Use the web page, or send it to /api/pdf/pages to turn it into images first.")
        if media_type is None:
            raise HTTPException(415, "Unsupported file. Use a JPG, PNG, WebP, or GIF image.")
        try:
            result = await run_in_threadpool(extractor.extract, data, media_type, layout)
        except ExtractionError as e:
            raise HTTPException(502, str(e)) from None
        log.info("extract ok: layout=%s columns=%d rows=%d", result.layout, len(result.columns), len(result.rows))
        return result

    @app.post("/api/pdf/pages", response_model=PdfPages)
    async def pdf_pages(request: Request, max_pages: int | None = Query(None, ge=1, alias="max")) -> PdfPages:
        """Body is the raw PDF. Returns its pages as images (the first `max`, at most the server's page limit).

        Needs no API key: this only draws pages. Each page image is then read through /api/extract like any photo.
        """
        data = await read_limited(request, settings.max_pdf_bytes, "PDF")
        if not data:
            raise HTTPException(400, "The file was empty.")
        if not looks_like_pdf(data):
            raise HTTPException(415, "That file is not a PDF.")
        limit = min(max_pages or settings.max_pdf_pages, settings.max_pdf_pages)
        try:
            result = await run_in_threadpool(render_pages, data, limit, settings.max_upload_bytes)
        except PdfError as e:
            raise HTTPException(422, str(e)) from None
        log.info("pdf ok: pages=%d rendered=%d", result.page_count, len(result.pages))
        return result

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()

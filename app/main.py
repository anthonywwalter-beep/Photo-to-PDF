"""Web app: serves the page and the /api/extract endpoint."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .extraction import AnthropicExtractor, DemoExtractor, ExtractionError, Extractor, sniff_media_type
from .schemas import Extraction, LayoutChoice

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
log = logging.getLogger("photo_to_table")


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
        limit = settings.max_upload_bytes
        too_big = HTTPException(413, f"File is too large. The limit is {limit // (1024 * 1024)} MB.")
        if int(request.headers.get("content-length") or 0) > limit:
            raise too_big
        buf = bytearray()
        async for chunk in request.stream():
            buf += chunk
            if len(buf) > limit:
                raise too_big
        data = bytes(buf)
        if not data:
            raise HTTPException(400, "The file was empty.")
        media_type = sniff_media_type(data)
        if media_type is None:
            raise HTTPException(415, "Unsupported file. Use a JPG, PNG, WebP, or GIF image.")
        try:
            result = await run_in_threadpool(extractor.extract, data, media_type, layout)
        except ExtractionError as e:
            raise HTTPException(502, str(e)) from None
        log.info("extract ok: layout=%s columns=%d rows=%d", result.layout, len(result.columns), len(result.rows))
        return result

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()

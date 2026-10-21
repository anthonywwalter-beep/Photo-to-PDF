# Changelog

Each entry lists every file touched and what the file is for. Newest first.

## 0.2.1 - Docs fix

| File | Change |
|---|---|
| `README.md` | Added Windows PowerShell instructions. The `curl -X` and `DEMO_MODE=1 uvicorn` examples only worked on macOS/Linux. |
| `CHANGELOG.md` | This entry. |

## 0.2.0 - Step 2: Extraction API

New endpoint `POST /api/extract`: send an image, get back a table. Works with a real key, or with `DEMO_MODE=1` and no key.

### Added
| File | Purpose |
|---|---|
| `app/config.py` | Reads settings from environment variables: API key, demo mode, model name, upload size limit. |
| `app/schemas.py` | Defines the response shape (`Extraction`: layout, columns, rows of `Cell{v, low}`). Later steps build the UI around it. |
| `app/extraction.py` | The core logic: builds the prompt, calls the reader, parses and validates its reply, pads short rows (flagging the missing cells), detects image type from bytes. Contains `AnthropicExtractor` (real) and `DemoExtractor` (sample data). |
| `tests/conftest.py` | Shared test fixture: a tiny valid PNG. |
| `tests/test_parsing.py` | Tests reply parsing: fenced JSON, ragged rows, bad output, image-type detection. |
| `tests/test_anthropic_extractor.py` | Tests the real extractor with a fake client: correct request, safe error messages. No network. |
| `tests/test_api.py` | Tests the endpoint: happy path, demo mode, missing key (503), empty (400), too large (413), wrong type (415), bad layout (422), reader failure (502), streaming size cap. |
| `tests/test_privacy.py` | Tests the privacy promises: no files written, document text never logged, large uploads never spooled to disk. |
| `CHANGELOG.md` | This file. |

### Changed
| File | Change |
|---|---|
| `app/main.py` | Added `/api/extract`, chooses the reader (demo / real / none), adds `Cache-Control: no-store` on API responses, and `/health` now reports `mode`. |
| `tests/test_health.py` | Updated for the new `/health` response and covers all three modes. |
| `requirements.txt` | Added `anthropic`. |
| `requirements-dev.txt` | Switched `httpx` to `httpx2`, which removes the test warning from step 1. |
| `.env.example` | Documents the new settings. |
| `README.md` | API reference, demo mode, settings, project layout. |
| `TODO.md` | Step 2 checked off. |

### Design decisions
- **Raw-body upload, not multipart.** The first version used a normal file-upload form. Testing showed the framework writes uploads over 1 MB to a temp file on disk, which would break the "nothing stored" promise for ordinary phone photos. The endpoint now reads the image bytes straight from the request stream into memory. A regression test guards this.
- **Image type comes from the bytes**, not the filename or the client's claim.
- **Errors never contain document text or API details**; logs record only counts and error class names.
- **Layout travels as a query parameter** (`?layout=auto|table|form|list`).

## 0.1.0 - Step 1: Scaffold

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app: `/health` and the static home page. |
| `app/__init__.py`, `tests/__init__.py` | Make the folders importable Python packages. |
| `static/index.html` | Placeholder home page; becomes the upload UI in step 3. |
| `tests/test_health.py` | Checks `/health` and the home page. |
| `requirements.txt`, `requirements-dev.txt` | Runtime and test dependencies. |
| `.env.example` | Template for settings. |
| `.gitignore` | Keeps `.env`, virtualenvs, and caches out of git. |
| `README.md` | What the project is, design principles, how to run it. |
| `TODO.md` | The step-by-step plan. |

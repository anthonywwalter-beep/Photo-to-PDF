# Changelog

Each entry lists every file touched and what the file is for. Newest first.

## 0.3.0 - Step 3: Upload page

You can now use the app in a browser: pick an image, see it beside the extracted table. Works in demo mode with no key.

### Added
| File | Purpose |
|---|---|
| `static/app.js` | The page's logic: validates the file, shows a local preview, sends the image to `/api/extract`, shows loading and error states, renders the result as a table, resets for another image, and reads `/health` to show a demo-mode or no-key banner. |
| `static/style.css` | Page styling: two-column layout (stacks on phones), loading spinner, error box, light and dark mode. |
| `tests/test_static.py` | Checks the page and assets are served, the privacy statement is present, every element id the script uses exists in the HTML, and the script never uses `innerHTML` (so text from a document can never inject markup). |

### Changed
| File | Change |
|---|---|
| `static/index.html` | Replaced the placeholder with the real page: privacy notice, drop zone, side-by-side Original / Extracted panes, raw JSON toggle. |
| `README.md` | Status line and instructions for using the web page. |
| `TODO.md` | Step 3 checked off. |
| `CHANGELOG.md` | This entry. |

### Design decisions
- **The page says which mode it is in.** Demo mode shows a banner so sample data is never mistaken for a real reading; with no key it explains how to fix that.
- **Cell text is inserted as plain text only.** A document could contain `<script>` or similar; it is displayed, never executed.
- **The preview never leaves the browser.** It comes from a local object URL; the image goes only to `/api/extract`.
- **Checks happen twice.** The page rejects non-images and files over 5 MB immediately; the server still enforces the same rules and its messages are shown as-is.
- **No framework or build step**, as planned in `docs/TECH_STACK.md`.

### Known limits (by design, for later steps)
The table is read-only (step 4), uncertain cells are not highlighted yet (step 5), there is no layout toggle (step 6), and only one image at a time (step 7). Photos in HEIC format (some iPhone settings) are rejected by the server with a clear message; use JPG or PNG.

### How it was verified
29 automated tests pass. The page script was also run in a simulated browser (jsdom) against the real demo server: 20 checks covering the full flow, loading state, rejected files, server and network errors, drag and drop, and hostile cell text. A simulated browser does not check how the page looks, so the visual layout still needs a look in a real browser.

## 0.2.2 - Tech stack document

| File | Purpose |
|---|---|
| `docs/TECH_STACK.md` | Records what the project uses now, what is planned per TODO step, what is deliberately left out and why, and the plan for Docker (recommended at step 11, not for development). |

| File | Change |
|---|---|
| `README.md` | Project layout table now lists `docs/` and `CHANGELOG.md`. |
| `TODO.md` | Step 8 names `pypdfium2`; step 10 names Pillow resizing; step 11 expanded with the Docker plan. |
| `CHANGELOG.md` | This entry. |

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

# Tech stack

Guiding rule: the fewest moving parts that keep the promises of the project (review step, nothing stored, photo in / table out). Anything that needs a database, accounts, or a build pipeline is left out on purpose.

## In use now (steps 1-2)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ (developed on 3.12) | Familiar to the maintainer; strong ecosystem for documents and images. |
| Web framework | FastAPI (on Starlette) | Small, fast, typed request/response models, easy to test. |
| Server | Uvicorn | Standard server for FastAPI. One process is enough for v1. |
| Reader (the AI) | Anthropic API via the official `anthropic` Python SDK, default model `claude-sonnet-5-5` | Reads photos and handwriting and returns structured JSON. Model is switchable with `EXTRACT_MODEL`. |
| Data shapes | Pydantic (ships with FastAPI) | Validates what the reader returns before the app trusts it. |
| Config | Environment variables | No config files with secrets; works the same locally and in Docker. |
| Tests | pytest + `httpx2` test client | All tests use fakes: no key, no network, no cost. |
| Version control | Git | One commit per TODO step. |

Last tested with: Python 3.12.3, FastAPI 0.143.3, Starlette 1.8.0, anthropic SDK 1.15.0. `requirements.txt` pins only minimum versions.

## Planned

| Step | Layer | Choice | Why |
|---|---|---|---|
| 3-7, 9 | Front end | Plain HTML, CSS, and JavaScript served from `static/` | No Node, no bundler, no build step. The page is small: upload, image beside an editable table, CSV button. |
| 4 | CSV export | Built in the browser (or Python `csv` module) | Needs no library. Data never has to be sent back to the server. |
| 8 | PDF to images | `pypdfium2` | Prebuilt wheels on Windows, macOS, and Linux with no system packages needed, and a permissive license. Alternatives considered: `pdf2image` (needs the Poppler program installed, awkward on Windows) and PyMuPDF (AGPL license, which would force open-sourcing any hosted service). |
| 10 | Image resizing | Pillow | Shrinks large phone photos before sending, which cuts cost and avoids the 5 MB limit. |
| 10 | Rate limiting | `slowapi` or a small in-memory limiter | Stops a public deployment being used to burn the API budget. In memory only, so it respects "nothing stored". |
| 11 | Packaging | Docker | See below. |

## Deliberately not used

| Not used | Reason |
|---|---|
| Database / ORM | Nothing is stored. This is the main privacy promise. |
| User accounts / sessions | Nothing to log into; nothing to leak. |
| Redis, queues, background workers | Each file is processed within one request. |
| React / Vue / Node build tools | Not needed for a one-screen tool; keeps setup to `pip install`. |
| Local OCR (Tesseract and similar) | Poor on handwriting, which is the core use case. Revisit only if a fully offline mode becomes a requirement. |

## Docker: recommended, at step 11

**Yes, it is possible, and it is recommended for deployment, not for day-to-day development.**

Why it helps here:
- One image runs the same on any host (a cloud service, a home server, a colleague's machine), with no "works on my machine" Python setup.
- It reinforces the privacy design. The container can run with a **read-only filesystem** and no volumes, so the "nothing is written to disk" promise is enforced by the platform and not just by our code.
- Secrets stay out of the image: the API key is passed at run time.

Why not use it for development now: on Windows, Docker Desktop adds a WSL2 dependency and slower reload cycles. A plain virtual environment is faster. Use Docker once there is something worth shipping.

### Plan for the Dockerfile (step 11)
- Base image `python:3.12-slim`. With `pypdfium2` and Pillow no extra system packages are needed.
- Run as a non-root user.
- Start with `uvicorn app.main:app --host 0.0.0.0 --port 8000`. (`0.0.0.0` is required inside a container; without it the app is unreachable from outside.)
- `.dockerignore` excludes `.env`, `.git`, `.venv`, and tests, so secrets never get baked into an image.
- `HEALTHCHECK` calls `/health`.
- Example run, which also proves nothing is stored:
  `docker run --read-only --tmpfs /tmp -p 8000:8000 -e ANTHROPIC_API_KEY=... photo-to-table`
- An optional `docker-compose.yml` for one-command local start.

### Things to decide when we get there
- **HTTPS is required for real use.** Documents are sensitive, so serve it behind HTTPS (a managed platform, or a reverse proxy such as Caddy).
- **Hosting platform logs.** The app logs no document content, but check that your host does not log request bodies.
- **Where the API key lives**: the host's secret store, not a file in the repo.

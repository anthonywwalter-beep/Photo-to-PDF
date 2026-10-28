# Photo to Table

Upload a photo or PDF of a table, form, or notes. Get an editable table next to the original, check it, and download a CSV.

## Status

Early development. Steps 1-4 are done: the server, the extraction API, the upload page, and an editable table with CSV download. Highlighting uncertain cells, the layout toggle, and multiple files come next. See [TODO.md](TODO.md) for the plan and [CHANGELOG.md](CHANGELOG.md) for what changed and why.

## How it will work

| Input | Output |
|---|---|
| Tables (sign-in sheets, logs, invoices) | Rows and columns |
| Forms (intake forms, applications) | One row per form, field labels as headers |
| Lists and free text (notes, flyers, letters) | A simple list of key items, dates, names, amounts |

Layout is picked automatically, with a "treat this as" toggle to correct it.

## Design principles

1. **Review first.** The original is shown beside the result, and cells the AI was unsure about are flagged. Handwriting is where mistakes happen.
2. **Nothing stored.** Files are processed in memory and discarded. No database, no accounts, no uploads written to disk, and request contents are not logged. Each page image is sent to the Anthropic API to be read, so deploy accordingly if your documents are sensitive.
3. **Photo in, clean table out.** No complex layouts, charts, or accounts in v1.

## Run it

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                             # no key or network needed
```

**Use the web page.** Start the server (see below), then open http://localhost:8000 in a browser, choose an image, and the original appears next to the extracted table. Click any cell or column name to fix it, delete or add rows, then press **Download CSV**. Edits live only in the open tab (nothing is saved), and the page warns you before they would be lost. With `DEMO_MODE=1` the table is sample data; with a key it is read from your image.

**Try it with no API key** (returns built-in sample data). Use any PNG or JPG; demo mode ignores its contents.

macOS / Linux:

```bash
DEMO_MODE=1 uvicorn app.main:app --reload
curl -X POST --data-binary @any-image.png "http://localhost:8000/api/extract?layout=form"
```

Windows PowerShell (`curl` there is a different command, so use these instead):

```powershell
.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned
$env:DEMO_MODE = "1"
uvicorn app.main:app --reload
```

Then in a second PowerShell window:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/extract?layout=form" `
  -InFile .\any-image.png -ContentType "application/octet-stream" | ConvertTo-Json -Depth 5
```

`curl.exe -X POST --data-binary "@any-image.png" "http://localhost:8000/api/extract?layout=form"` also works on Windows 10 and later (note the `.exe`).

**Run it for real:** copy `.env.example` to `.env`, add `ANTHROPIC_API_KEY`, then:

```bash
uvicorn app.main:app --reload --env-file .env
curl -X POST --data-binary @photo.jpg http://localhost:8000/api/extract
```

## API

`POST /api/extract?layout=auto|table|form|list`

The request body is the raw image (JPG, PNG, WebP, or GIF, up to 5 MB). The image type is detected from the bytes.

```json
{"layout": "table",
 "columns": ["Name", "Time in"],
 "rows": [[{"v": "Maria Lopez", "low": false}, {"v": "9:0?", "low": true}]]}
```

`low: true` means the reader was unsure about that cell. Errors: `400` empty, `413` too large, `415` not an image, `422` bad layout, `502` reader failed, `503` no key configured.

`GET /health` returns `{"ok": true, "mode": "demo" | "live" | "no-key"}`.

## Settings

| Variable | Meaning |
|---|---|
| `ANTHROPIC_API_KEY` | Enables real reading |
| `DEMO_MODE=1` | Sample data, no key needed |
| `EXTRACT_MODEL` | Model name (default `claude-sonnet-5-5`) |
| `MAX_UPLOAD_MB` | Upload limit (default 5) |

## Project layout

| Path | Purpose |
|---|---|
| `app/main.py` | Web app and endpoints |
| `app/extraction.py` | Prompt, reader (real and demo), reply parsing |
| `app/schemas.py` | Response shape |
| `app/config.py` | Settings from environment |
| `static/` | The web page |
| `docs/TECH_STACK.md` | Tech stack, what is deliberately left out, Docker plan |
| `CHANGELOG.md` | Every change, with each file's purpose |
| `tests/` | Automated tests; none need a key or network |

# Changelog

Each entry lists every file touched and what the file is for. Newest first.

## 0.7.0 - Step 7: Multiple files

Several images can be uploaded at once and are merged into one table. Click a row to see the image it came from. No server change: each image is still one `/api/extract` request.

### Added
| File | Purpose |
|---|---|
| `scripts/smoke_live.py` | Live smoke test: reads real image files through the real API and prints layout, counts, flagged cells, timing, and the first rows. Needs a key; costs a few cents. Takes a fake reader in tests. |
| `tests/test_smoke_script.py` | Tests the smoke script with a fake reader: output, exit codes, unreadable and non-image files, missing key. |
| `docs/LIVE_TESTING.md` | How and when to test with a real key: safety steps, what to run, what to look for, what to write down. |

### Changed
| File | Change |
|---|---|
| `static/app.js` | Rewritten around a list of images and one merged table. Up to 20 images per batch, read 3 at a time, results added as they arrive but always kept in image order. Per-image failures with a "Try again" button. Image tabs, a source-image number on each row, a "Source image" CSV option, "Add more images", and "Start over". |
| `static/index.html` | Multi-file picker, image tabs, "Add more images", per-image problem list, the CSV source option. |
| `static/style.css` | Tabs, problem boxes, the source-number column. |
| `tests/test_static.py` | New test: the file picker must accept several files. |
| `README.md`, `TODO.md`, `CHANGELOG.md` | Status, step 7 checked off, this entry. |

### Design decisions
- **Column matching.** Columns from different images are matched by name, ignoring case and spacing, in any order. Unmatched names become new columns, and rows from images without that column get blanks (not flagged). The match key is fixed when the column is created, so renaming a header later does not stop later images from landing in it. Two columns with the same name on one page stay separate.
- **Image order always wins.** Rows are placed by image number, not arrival time, so a slow first image still appears first. A retried image slides back into its place.
- **One bad image does not block the rest.** Failed images are listed with the reason and a "Try again" button; the others show normally.
- **Typing is not interrupted.** Answers can arrive while someone is editing; the table is redrawn but the cursor, selection, and focus are put back.
- **Changing layout re-reads every image**, and the page says how many ("Reading all 3 images again..."). Nothing on screen changes until the answers are in; if every re-read fails the old table and edits are kept; if only some fail the rest replace the table and the failed ones are listed.
- **Bounded cost and memory.** At most 20 images per batch, 3 requests at a time, and the layout toggle and "Add more images" are locked while reading. Invalid or oversize files are skipped with a note naming each one.
- **File names are untrusted text.** They appear only as text, and in the CSV source column they get the same spreadsheet-formula protection as every other cell.
- **The source column is opt-in.** File names can contain personal details, so the CSV only includes them if the box is ticked.
- **PDFs are still rejected**, with the same message as any non-image; step 8 adds them.

### How it was verified
41 automated tests pass (also with Python's default text encoding forced to ASCII). The page was run in a simulated browser (jsdom), partly against the real demo server and partly with scripted slow, failing, and out-of-order answers: 77 checks covering merging, ordering, the 3-at-a-time limit, column matching, failures and retries, layout changes (cancel, confirm, partial and total failure), adding images, not disturbing typing, skipped files and the 20-image cap, "Start over" with a late answer, hostile file names, and the step 4 to 6 features on merged rows. Five deliberate bugs (case-sensitive matching, rows appended instead of ordered, cursor not restored, late answers not ignored, no concurrency limit) were each caught, then the code was restored. A simulated browser cannot judge appearance, so please check the layout, especially the tabs and the Img column, in a real browser and on a narrow screen.

### Known limits
Column matching is by name only. If the real reader labels the same field differently on different pages, the page will show two columns and the user must fix it by hand (there is no "merge columns" button yet). Whether that happens with real documents can only be learned with a real key; see `docs/LIVE_TESTING.md`. No PDFs yet (step 8). Browser memory holds all images at once, so 20 images of 5 MB is about 100 MB.

## 0.6.0 - Step 6: Layout toggle

A "Treat this as: Auto / Table / Form / List" control lets the user correct the tool when it guesses the layout wrong. No server change: `/api/extract` has accepted `?layout=` since step 2.

### Changed
| File | Change |
|---|---|
| `static/app.js` | Reading was split out so it can be repeated. The chosen image stays in the browser tab, and picking a layout sends it again with `?layout=`. The summary says "Detected layout" for Auto or "Layout (your choice)" otherwise. |
| `static/index.html` | Added the four-option radio group and a one-line explanation of each layout. |
| `static/style.css` | Pill-style radio buttons, a dimmed table while reading. |
| `tests/test_static.py` | New test: the page's toggle must offer exactly the layouts the API accepts (checked against `LayoutChoice`), so the two cannot drift apart. |
| `README.md`, `TODO.md`, `CHANGELOG.md` | Status, step 6 checked off, this entry. |

### Design decisions
- **A failed re-read changes nothing.** The current table and your edits stay on screen, the toggle snaps back to its previous value, and an error is shown. Only a successful read replaces the table.
- **Edits are never silently lost.** If there are unsaved edits, the page asks before re-reading, and cancelling leaves everything as it was. With no edits it just re-reads.
- **One read at a time.** The toggle is disabled and the table dimmed while a read is running, so rapid clicking cannot start several paid API calls. Re-selecting the current option does nothing.
- **Late answers are ignored.** Each read has a number; if the user has since moved on (chose another image, started another read), an answer that arrives afterwards is discarded.
- **The image is resent, not stored.** It is held in memory in the browser tab only and sent to the server again on each re-read. The server still keeps nothing. Each re-read is another call to the Anthropic API, which matters for cost in live mode.
- **Not colour alone.** The selected option is also bold.

### How it was verified
36 automated tests pass (also with Python's default text encoding forced to ASCII). The page was run in a simulated browser (jsdom) against the real demo server: 34 checks covering the request sent for each choice, the image bytes being resent, new tables per layout, the busy state, the unsaved-edit question (cancel and confirm), server and network failures keeping the old table, a late answer after "choose another", and the step 4 and 5 features afterwards. Three deliberate bugs (choice never sent, toggle not reverting after an error, late answers not ignored) were each caught, then the code was restored.

### Known limits
In demo mode each layout returns fixed sample data regardless of the image, so the toggle can be tried but says nothing about real accuracy. With a real key, a forced layout is an instruction to the reader; it follows it well in most cases but nothing in the server yet enforces, for example, exactly one row for a form. Whether forced layouts read real documents better than Auto can only be judged with real documents. Still one image at a time (step 7).

## 0.5.0 - Step 5: Uncertain-cell flags

Cells the reader was unsure about are highlighted so a person can check them quickly against the original.

### Added
| File | Purpose |
|---|---|
| `tests/test_demo.py` | Makes sure demo mode includes uncertain cells in every layout, so the whole review flow can be tried without an API key. |

### Changed
| File | Change |
|---|---|
| `static/app.js` | Flagged cells are highlighted. A live counter shows how many are left ("3 cells to check"), a **Next cell to check** button jumps between them in reading order and wraps around, and a **✓** button marks a cell as correct without changing it. Editing a flagged cell also clears its flag. Downloading with unchecked flags works but says how many were not checked. |
| `static/index.html` | Added the Next button, the counter, and a legend explaining amber cells and the ✓. |
| `static/style.css` | Amber highlight (light and dark mode), the ✓ button, the legend swatch. |
| `README.md`, `TODO.md`, `CHANGELOG.md` | Status, step 5 checked off, this entry. |

### Design decisions
- **A flag clears only when the user acts.** Editing the cell or pressing ✓ clears it; clicking into it or tabbing past does not. The tool never assumes a cell was reviewed just because it was looked at.
- **Not colour alone.** Flagged cells also have a thick left edge, a hover tooltip, a ✓ button, a screen-reader label ("uncertain, please check"), and the counter, so the cue survives colour blindness and printing in black and white.
- **Flags never enter the CSV.** The file contains only the data. Unchecked flags produce a note when downloading, not a block, because the person may have a good reason to download early.
- **Flags travel with their row.** Deleting a flagged row lowers the count; Undo brings the row and its flags back. Added rows start unflagged.
- **The ✓ counts as an edit** for the unsaved-work warning, since it is review work that would be lost.

### How it was verified
35 automated tests pass (also with Python's default text encoding forced to ASCII, the check that caught the Windows bug). The page was run in a simulated browser (jsdom) against the real demo server: 30 checks covering highlighting, clearing by edit and by ✓, focus-only not clearing, the Next button including wrap-around, flags through delete, undo, and add row, no flag data in the CSV, and the step 4 features after the cell code changed. To confirm those checks can actually fail, two deliberate bugs were introduced (edits not clearing flags; Next never advancing) and both were caught, then the code was restored. A simulated browser cannot judge how the colours look, so please check the amber highlight in a real browser in light and dark mode.

### Known limits
Whether a cell is flagged is the reader's own judgement. It will sometimes flag a correct cell and may miss a wrong one, so the original image still needs a look. Columns cannot yet be added or deleted. One image at a time (step 7).

## 0.4.1 - Fix: tests failed on Windows

Three tests in `tests/test_static.py` failed on Windows with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d`.

**Cause:** the tests read `static/app.js` and `static/index.html` with `Path.read_text()` and no encoding. Python then uses the operating system's default, which is UTF-8 on Linux and macOS but cp1252 on Windows. Step 4 added characters such as the multiplication sign and curly quotes to the web files, which cp1252 cannot decode. It was missed because all earlier testing ran on Linux. The app itself was not affected: the server already sends `charset=utf-8` for the page, script, and stylesheet.

| File | Change |
|---|---|
| `tests/test_static.py` | All four `read_text()` calls now pass `encoding="utf-8"`. |
| `tests/test_hygiene.py` | New. Fails if any Python file under `app/` or `tests/` calls `read_text` or `write_text` without an explicit encoding, so this cannot come back unnoticed. |
| `CHANGELOG.md` | This entry. |

**Verified by** reproducing the exact three failures with the default encoding forced to ASCII, confirming all tests pass under that setting after the fix, and confirming the new guard test fails when the bug is reintroduced. 31 tests pass. Not run on an actual Windows machine.

## 0.4.0 - Step 4: Editable table and CSV download

The extracted table can now be corrected in the page and downloaded as a CSV. Everything happens in the browser tab; edits and the CSV are never sent to the server.

### Changed
| File | Change |
|---|---|
| `static/app.js` | Rewritten around an editable table held in memory. Cells and column names are editable; rows can be deleted (with Undo) and added; Enter moves down a row; the CSV is built and downloaded in the browser; leaving the page or loading another image with unsaved edits asks first. |
| `static/index.html` | Added the toolbar (+ Add row, Download CSV), a hint line, and the Undo bar. The raw JSON toggle is now labelled "as read, before your edits". |
| `static/style.css` | Styles for editable cells (look like plain cells, highlight on focus), the toolbar, the primary button, and the Undo bar. |
| `tests/test_static.py` | Added a guard test: the script may never use localStorage, sessionStorage, IndexedDB, or cookies, so the "nothing stored" promise holds in the browser too. |
| `README.md` | Status line and a note on editing and CSV. |
| `TODO.md` | Step 4 checked off. |
| `CHANGELOG.md` | This entry. |

### Design decisions
- **Spreadsheet formula protection.** Document text is untrusted: a form could contain `=HYPERLINK(...)`, which Excel and Sheets run when the CSV is opened. Cells (and headers) starting with `=`, `@`, tab, or carriage return, or with `+`/`-` followed by anything other than digits and number punctuation, get a leading `'`. Plain numbers and phone numbers such as `-5.00` or `+1 (555) 014-2` are left untouched. The page tells the user this.
- **CSV format.** Comma separated, CRLF line endings, fields containing commas, quotes, or line breaks are quoted, and a UTF-8 byte-order mark is added so Excel shows accents and non-English text correctly.
- **Edits are not saved anywhere, so the page protects them**: a browser warning before closing or reloading with unsaved edits, a confirmation before replacing the table with another image, and a one-step Undo for a deleted row.
- **Input fields, not rich text.** Cells are plain text areas, so pasted content can never carry formatting or markup.
- **Confidence flags are kept in memory** (`low` on each cell, cleared when a cell is edited) ready for step 5, which will highlight them. Nothing displays them yet.
- **No server change.** The CSV is built in the browser, as planned in `docs/TECH_STACK.md`.

### How it was verified
30 automated tests pass. The page was also run in a simulated browser (jsdom) against the real demo server: 28 checks covering editing, renaming, delete and undo, add row, Enter-key movement, unsaved-edit warnings, and the actual downloaded bytes (byte-order mark, CRLF, quoting, accents, and 8 kinds of formula-looking cells). Those browser checks are not part of the repository, because the project does not use Node. The Python tests only cover the static files. A simulated browser also cannot judge appearance or a real file download, so please try both in a real browser.

### Known limits
Columns cannot be deleted or added yet. The table is still one image at a time (step 7).

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

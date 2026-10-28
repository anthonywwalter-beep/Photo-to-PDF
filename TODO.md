# TODO

Work one step at a time. Each step ends with something runnable and a git commit.

- [x] **1. Scaffold.** Repo, FastAPI server that serves a static page, `/health` endpoint, test, README with privacy stance.
- [x] **2. Extraction API.** `POST /api/extract` takes one image in memory, calls the Anthropic API, returns `{layout, columns, rows}` where each cell is `{v, low}`. Demo mode works with no key. No disk writes, no content logging.
- [x] **3. Upload page.** Pick one image, show it beside the raw extracted result. Loading and error states.
- [x] **4. Editable table + CSV.** Edit cells, rename columns, delete/add rows, download CSV.
- [ ] **5. Uncertain-cell flags.** Highlight low-confidence cells; editing clears the flag.
- [ ] **6. Layout toggle.** Auto-detect table/form/list, with a "treat this as" override that re-runs extraction.
- [ ] **7. Multiple files.** Several images at once, merged into one table; click a row to see its source image.
- [ ] **8. PDF support.** Convert PDF pages to images in memory with `pypdfium2`, then treat them as step 7 does.
- [ ] **9. Printable view.** Clean print stylesheet.
- [ ] **10. Hardening.** File size/type limits, Pillow downscaling of large photos, rate limiting, error messages, privacy checks (no logs of content), tests.
- [ ] **11. Deploy docs.** Dockerfile (slim base, non-root, `--host 0.0.0.0`, `.dockerignore`, healthcheck), optional compose file, run with `--read-only` to enforce nothing-stored, HTTPS notes. See `docs/TECH_STACK.md`.

Out of scope for v1: multi-column newsletters, charts/graphs, accounts, databases.

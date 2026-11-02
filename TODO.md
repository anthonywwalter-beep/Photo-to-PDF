# TODO

Work one step at a time. Each step ends with something runnable and a git commit.

- [x] **1. Scaffold.** Repo, FastAPI server that serves a static page, `/health` endpoint, test, README with privacy stance.
- [x] **2. Extraction API.** `POST /api/extract` takes one image in memory, calls the Anthropic API, returns `{layout, columns, rows}` where each cell is `{v, low}`. Demo mode works with no key. No disk writes, no content logging.
- [x] **3. Upload page.** Pick one image, show it beside the raw extracted result. Loading and error states.
- [x] **4. Editable table + CSV.** Edit cells, rename columns, delete/add rows, download CSV.
- [x] **5. Uncertain-cell flags.** Highlight low-confidence cells; editing clears the flag.
- [x] **6. Layout toggle.** Auto-detect table/form/list, with a "treat this as" override that re-runs extraction.
- [x] **7. Multiple files.** Several images at once, merged into one table; click a row to see its source image.
- [x] **8. PDF support.** Convert PDF pages to images in memory with `pypdfium2`, then treat them as step 7 does.
- [ ] **9. Printable view.** Clean print stylesheet.
- [ ] **10. Hardening.** File size/type limits, Pillow downscaling of large photos, rate limiting, error messages, privacy checks (no logs of content), tests.
- [ ] **11. Deploy docs.** Dockerfile (slim base, non-root, `--host 0.0.0.0`, `.dockerignore`, healthcheck), optional compose file, run with `--read-only` to enforce nothing-stored, HTTPS notes. See `docs/TECH_STACK.md`.

Out of scope for v1: multi-column newsletters, charts/graphs, accounts, databases.

## Phase 2: Private processing (after step 11)

Do these only after steps 1-11 are complete. Until then the app tells users **not to upload sensitive information**, because in live mode images go to the Anthropic API and may be retained under its policies. Background, options, and open questions: [docs/PRIVATE_PROCESSING.md](docs/PRIVATE_PROCESSING.md).

- [ ] **12. Privacy basics.** Strip photo metadata before sending (apply the EXIF rotation first so photos do not turn sideways), reword the privacy text to separate what this app stores from what the reading service may keep, show the mode on the page (private or cloud), and add an opt-in notice before the first cloud upload. Re-check reading accuracy after re-encoding.
- [ ] **13. Reader setting.** `READER=anthropic|local`. The local reader sends the image to a model server on the same machine or network (for example Ollama) with the same instructions and expects the same table format. **No silent fallback:** if local is configured and unavailable, show an error and never send to the cloud. Tests use fakes.
- [ ] **14. Scoring and checkpoint.** A script that runs the sample documents in `samples/` (with answer keys; to be added) through each reader and scores cells correct and whether wrong cells were flagged. Run by the user on their own hardware. Decision: stay with a general local vision model, or build step 15.
- [ ] **15. (Only if step 14 says so) Dedicated OCR pipeline.** A dedicated local OCR model for reading, our own code for rows, columns, forms, and lists, and the OCR engine's confidence scores as the flags. Check model licences first.
- [ ] **16. Closed deployment profile.** Docker compose with the app and the model server on an internal network that has no internet access, models pre-loaded, read-only filesystem, and a test that proves the app container cannot reach out. Guidance for access control (login or VPN), since the app has no accounts.
- [ ] **17. (Optional) Cloud with stricter terms.** Document how to arrange zero data retention or HIPAA readiness with Anthropic; build an alternative cloud reader only if needed.
- [ ] **18. Retire the interim warning.** Replace the "do not upload sensitive information" warning with a notice that matches the deployment's actual mode, only after steps 12-16 are verified for it. In cloud mode without a ZDR or HIPAA arrangement, a warning stays.

# Testing with a real API key

Everything so far is tested with fakes and demo data. The one thing no test here can check is the real call to the Anthropic API: whether the model name is accepted, whether the reply parses, how good the "unsure" flags are, how consistent column names are from page to page, how long a read takes, and what it costs. This guide is how to check those.

## Before you start

- **Use sample documents first.** The image goes to the Anthropic API, and the smoke script prints what it read to your terminal. Make or find a few harmless samples (a printed table, a handwritten sign-in sheet you write yourself, a blank-ish intake form you fill with made-up details).
- **Put a spend limit on the key.** Create a key just for this project and set a monthly limit in the Anthropic console. A smoke test costs a few cents; a bug that loops could cost more.
- **Keep the key out of git.** Copy `.env.example` to `.env` and add `ANTHROPIC_API_KEY=...`. `.env` is already in `.gitignore`. Never paste the key into a chat or an issue.

## 1. Smoke test from the command line (about 5 minutes)

```bash
python scripts/smoke_live.py sample-table.jpg sample-form.jpg --layout auto
```

For each image it prints the layout it chose, row and column counts, how many cells were flagged, how long the read took, and the first rows (a trailing `?` marks a flagged cell). It exits with an error code if any image failed.

| If you see | It probably means |
|---|---|
| `No ANTHROPIC_API_KEY found` | The key is not in the environment or `.env`. |
| `FAILED: The reading service could not process this image` | The call itself failed: wrong model name (set `EXTRACT_MODEL`), invalid key, no credit, or no network. Run the server with `--log-level info` to see the error class (document text is never logged). |
| `FAILED: The reader returned something unreadable` | The model's reply was not the JSON we asked for. Note which image; this is the most useful thing to report. |
| Few or no flagged cells on a messy handwritten sample | The reader is over-confident. Worth knowing before trusting flags. |

## 2. Try the page with the key (about 10 minutes)

Start the server without demo mode: `uvicorn app.main:app --reload --env-file .env`. Open http://localhost:8000. The banner about demo mode should be gone.

1. Upload one clear printed table. Does the table match?
2. Upload one handwritten page. Are the amber cells the doubtful ones?
3. Upload **two or three pages of the same kind** (several copies of the same form, or pages of one long table). This is the test that matters most for merging: do the columns line up, or does the same field come back with slightly different names ("Full name" vs "Name") and split into two columns?
4. Try the **Treat this as** toggle on one image. Does a forced layout behave (a form giving exactly one row)?
5. Upload a big phone photo (3 to 5 MB). Note how long it takes.

## What to write down

- Time per image (this decides concurrency and timeouts).
- Anything that failed, and the exact message.
- Column names that differ between pages of the same form.
- Cells that were wrong but not flagged, and flagged cells that were right.
- Rough cost: check the usage page in the Anthropic console before and after.

## When to do this

As early as possible, and certainly before step 8 (PDFs) and step 10 (hardening). PDF support feeds pages through the same reader, and the limits in step 10 (image downscaling, rate limits, timeouts) should be set from real timings and costs, not guesses.

# Photo to Table

Upload a photo or PDF of a table, form, or notes. Get an editable table next to the original, check it, and download a CSV.

## Status

Early development. See [TODO.md](TODO.md) for the step-by-step plan.

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
cp .env.example .env               # add your key (needed from step 2)
uvicorn app.main:app --reload      # http://localhost:8000
pytest
```

# Sample documents

Made-up test documents for Photo to Table, with an answer key for each. Every name, phone number, address, and amount is invented (phone numbers use the reserved 555-01xx range). Nothing here is, or resembles, real personal data, so these are safe to send to the Anthropic API.

**The handwriting is simulated** (each letter is drawn slightly tilted, sized, and shifted). It is a rough stand-in. Real handwriting, from real people, on real paper, is harder, so treat a good result here as a minimum, not a guarantee.

Regenerate or change them with `python samples/make_samples.py` (needs `pip install pillow`). The answer keys are written from the same data used to draw the pictures, so they cannot drift apart. `--big` also creates two oversize photos in `samples/big/` (git-ignored).

## What is here and what to look for

| File | Tests | A good result |
|---|---|---|
| `01_signin_printed.png` | Clean printed table. The easy baseline. | 6 rows, 4 columns, matching `expected_01_signin_printed.csv`. Few or no amber cells. |
| `02_signin_messy_photo.jpg` | Tilted phone photo, uneven light, wobbly writing. | Matches `expected_02_signin_messy_photo.csv` except the two hard cells below, which should be **amber**. |
| `03_intake_form_a.png` `04_intake_form_b.jpg` `05_intake_form_c.png` | The same form filled in three times (b is a photo). This is the **merging test**. | Upload all three together. Read as a form, they merge into 3 rows and the same 6 columns (`expected_03-05_intake_forms.csv`). If the same field comes back named differently on different pages you will see extra columns: note which. |
| `06_invoice_photo.jpg` | Line items with numbers, photographed. | The 5 line items in `expected_06_invoice_photo.csv`. The subtotal, tax, and total under the table may appear as extra rows or be left out; either is acceptable. Check that amounts are exact. |
| `07_meeting_notes.png` | Free text, for the **List** layout. | Key items by type. Check these are found: dates Oct 15 2026, Nov 7, Oct 23, Nov 12 2026 (7:00 pm); names Dana Whitfield, Luis Ortega, Priya Nair, Tom Becker; amounts $320, $85, $42.50 (and 40 chairs, 150 flyers). No answer key: judge by whether the important items are there and nothing is invented. |
| `08_blank_page.png` | A page with nothing on it. | An **error or empty result**, not a made-up table. Any invented data here is a real problem. |
| `09_forms_3pages.pdf` | The three intake forms as one 3-page PDF. | Becomes 3 tabs ("... - page 1" to "... - page 3") and the same result as the three separate images. |
| `10_signin_2pages_scan.pdf` | A 2-page "scanned" sign-in sheet (phone-photo style), header repeated on page 2. | 9 rows in order, page 1 then page 2 (`expected_10_signin_2pages_scan.csv`). The repeated header on page 2 must not appear as a data row. |
| `big/big_photo_4mb.jpg` | A 4.3 MB photo, under the limit. | Reads normally. Note how long it takes. |
| `big/too_big_6mb.jpg` | A 5.8 MB photo, over the 5 MB limit. | Skipped with a "larger than 5 MB" message, with no request sent. |

## The two deliberately hard cells in `02_signin_messy_photo.jpg`

- **Beatriz Santos, Initials:** an illegible scribble. The key says empty. A good reader leaves it empty or flags it. A reader that confidently invents initials is the failure to watch for.
- **Wei Zhang, Time out:** the writing is cut off at the edge of the cell and shows only "12:". The true value is 12:25. A good reader flags it. Writing a confident "12:00" is the failure.

## How to judge a run

For each document, compare the table with its answer key and count:

1. **Cells correct.**
2. **Cells wrong and flagged** (the tool warned you).
3. **Cells wrong and not flagged.** This is the number that matters most: an error you were not warned about is the one that gets into a spreadsheet.

Write the counts down for each reader you try. `docs/PRIVATE_PROCESSING.md` explains why this comparison is planned for local models too.

## Ways to run them

- **The web page:** drop one file, several files, or the PDFs. Upload 03 to 05 together to test merging, and try the Treat this as toggle.
- **The command line:** `python scripts/smoke_live.py samples/01_signin_printed.png samples/10_signin_2pages_scan.pdf` (needs your key; PDFs are converted to pages first).
- **Demo mode** (no key) accepts all of them too, but returns sample data, so it only tests the plumbing.

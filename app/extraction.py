"""Turn an image into an Extraction. Everything happens in memory.

Pieces:
  build_prompt        - the instructions sent with the image
  parse_model_output  - turn the model's reply into a validated Extraction
  sniff_media_type    - identify the image from its bytes, not the client's claim
  AnthropicExtractor  - the real reader (needs an API key)
  DemoExtractor       - canned results so the app can be tried with no key
Anything with an `extract(image, media_type, layout)` method works as an extractor,
which is how the tests swap in fakes.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Protocol

from .schemas import Cell, Extraction

log = logging.getLogger("photo_to_table")


class ExtractionError(Exception):
    """Raised with a message that is safe to show the user (never contains document text)."""


class Extractor(Protocol):
    def extract(self, image: bytes, media_type: str, layout: str) -> Extraction: ...


# ---------- image type ----------
def sniff_media_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


# ---------- prompt ----------
_FORCED = {
    "table": "Treat this as a TABLE: rows and columns as laid out on the page.",
    "form": "Treat this as a FORM: output exactly ONE row. Column headers are the field labels; cells are the filled-in values.",
    "list": 'Treat this as a LIST or free text: use columns ["Type","Item"], one row per key item. '
            "Type is one of Date, Name, Amount, Task, Note, Other.",
}
_AUTO = (
    "First decide the layout. \"table\" = sign-in sheets, logs, invoices with line items. "
    "\"form\" = a single filled-in form: field labels become columns, ONE row. "
    "\"list\" = notes, flyers, letters: columns [\"Type\",\"Item\"], one row per key item, date, name, or amount."
)


def build_prompt(layout: str) -> str:
    return (
        "You read photographed or scanned documents and extract their content. Look at the attached image.\n"
        f"{_AUTO if layout == 'auto' else _FORCED[layout]}\n"
        "Rules: transcribe exactly what is written; never invent values; leave unreadable or empty cells as \"\". "
        'For every cell set "low": true if handwriting is messy, text is blurry or cut off, or you are guessing; otherwise false.\n'
        'Reply with ONLY JSON, no markdown: {"layout":"table|form|list","columns":["..."],'
        '"rows":[[{"v":"cell text","low":false}]]}\n'
        "Every row must have exactly as many cells as columns."
    )


# ---------- parsing ----------
def _cell(x) -> Cell:
    if isinstance(x, dict):
        v = x.get("v")
        return Cell(v="" if v is None else str(v), low=bool(x.get("low", False)))
    return Cell(v="" if x is None else str(x))


def parse_model_output(text: str, layout_hint: str = "auto") -> Extraction:
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ExtractionError("The reader did not return a table. Try again or use a clearer photo.")
    try:
        raw = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        raise ExtractionError("The reader returned something unreadable. Try again.") from None
    if not isinstance(raw, dict):
        raise ExtractionError("The reader returned something unreadable. Try again.")

    columns = [str(c).strip() for c in (raw.get("columns") or [])]
    if not columns:
        raise ExtractionError("No columns were found in this image.")

    rows = []
    for r in raw.get("rows") or []:
        if not isinstance(r, list):
            continue
        cells = [_cell(x) for x in r][: len(columns)]
        cells += [Cell(v="", low=True)] * (len(columns) - len(cells))  # missing cells get flagged
        rows.append(cells)

    layout = layout_hint if layout_hint != "auto" else raw.get("layout")
    if layout not in ("table", "form", "list"):
        layout = "table"
    return Extraction(layout=layout, columns=columns, rows=rows)


# ---------- real reader ----------
class AnthropicExtractor:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-5-5", client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        self._client = client
        self._model = model

    def extract(self, image: bytes, media_type: str, layout: str) -> Extraction:
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                       "data": base64.b64encode(image).decode()}},
                        {"type": "text", "text": build_prompt(layout)},
                    ],
                }],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        except Exception as e:  # never log or echo the document; the class name is enough
            log.warning("reader call failed: %s", type(e).__name__)
            raise ExtractionError("The reading service could not process this image. Try again in a moment.") from None
        return parse_model_output(text, layout)


# ---------- demo reader ----------
_DEMO = {
    "table": Extraction(layout="table", columns=["Name", "Time in", "Time out", "Signature"], rows=[
        [Cell(v="Maria Lopez"), Cell(v="9:02"), Cell(v="11:30"), Cell(v="M. Lopez")],
        [Cell(v="J. Whitfeld", low=True), Cell(v="9:15"), Cell(v="10:4?", low=True), Cell(v="", low=True)],
        [Cell(v="Aisha Khan"), Cell(v="9:40"), Cell(v="12:00"), Cell(v="A. Khan")],
    ]),
    "form": Extraction(layout="form", columns=["Full name", "Phone", "Date of birth", "Reason for visit"], rows=[
        [Cell(v="Daniel Okafor"), Cell(v="555-0142", low=True), Cell(v="03/14/1988"), Cell(v="Housing assistance")],
    ]),
    "list": Extraction(layout="list", columns=["Type", "Item"], rows=[
        [Cell(v="Date"), Cell(v="Nov 12, 2026")],
        [Cell(v="Name"), Cell(v="Pat Rivera")],
        [Cell(v="Amount"), Cell(v="$250.00", low=True)],
    ]),
}


class DemoExtractor:
    """Returns sample data. Ignores the image. For trying the app without an API key."""

    def extract(self, image: bytes, media_type: str, layout: str) -> Extraction:
        return _DEMO["table" if layout == "auto" else layout].model_copy(deep=True)

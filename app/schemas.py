"""The shape of what /api/extract returns. Every later step builds on this."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Layout = Literal["table", "form", "list"]
LayoutChoice = Literal["auto", "table", "form", "list"]


class Cell(BaseModel):
    v: str = ""          # the text in the cell
    low: bool = False    # True when the reader was unsure (messy handwriting, blur, guessing)


class Extraction(BaseModel):
    layout: Layout
    columns: list[str]
    rows: list[list[Cell]]  # every row has exactly len(columns) cells


class PdfPage(BaseModel):
    media_type: str       # always image/jpeg
    width: int
    height: int
    data: str             # the page image, base64


class PdfPages(BaseModel):
    page_count: int       # pages in the PDF
    pages: list[PdfPage]  # the pages rendered (at most the page limit)

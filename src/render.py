"""Turn a PDF into page images for the vision model.

Why images instead of extracted text: the Deye spec table is a dense multi-column
grid. Plain text extraction interleaves the columns, so the 5 kW value can end up
next to the wrong model. A vision model reads the page as laid out and can pick
the correct column. We render *every* page (these sheets are 2 pages) rather than
hardcoding "page 2", so a re-laid-out revision still works.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pymupdf

from .config import DATA_DIR, RENDER_DPI


def render_pdf_to_images(pdf_path: Path, dpi: int = RENDER_DPI) -> list[Path]:
    """Render each page of the PDF to a PNG and return the image paths."""
    doc = pymupdf.open(pdf_path)
    out: list[Path] = []
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            img_path = DATA_DIR / f"{pdf_path.stem}_p{i + 1}.png"
            pix.save(img_path)
            out.append(img_path)
    finally:
        doc.close()
    return out


def image_to_data_uri(img_path: Path) -> str:
    """Base64 data URI, ready to hand to a multimodal LLM message."""
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"

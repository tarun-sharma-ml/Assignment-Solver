"""PDF reader: uses the text layer when present, otherwise OCRs each page."""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from .image_ocr import ocr_pil_image


def read_pdf(path: str | Path, min_chars_per_page: int = 25) -> str:
    pages: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            text = page.get_text("text").strip()
            if len(text) < min_chars_per_page:  # scanned page -> OCR
                pix = page.get_pixmap(dpi=250)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                text = ocr_pil_image(img).strip()
            pages.append(text)
    return "\n\n".join(p for p in pages if p)

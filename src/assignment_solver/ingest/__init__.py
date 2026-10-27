"""Read an assignment from (almost) any file and return plain text."""
from __future__ import annotations

from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
TEXT_EXTS = {".txt", ".md", ".rst", ".csv"}


def load_text(path: str | Path) -> str:
    """Extract text from a PDF, DOCX, image or text file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        from .pdf import read_pdf

        return read_pdf(path)
    if ext == ".docx":
        from .docx_reader import read_docx

        return read_docx(path)
    if ext in IMAGE_EXTS:
        from .image_ocr import read_image

        return read_image(path)
    if ext in TEXT_EXTS:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(
        f"Unsupported file type '{ext}'. Supported: .pdf, .docx, images "
        f"({', '.join(sorted(IMAGE_EXTS))}), {', '.join(sorted(TEXT_EXTS))}"
    )

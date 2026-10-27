"""OCR for photos/screenshots of assignments using Tesseract (free, runs locally)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps
import os
import shutil


def _configure_tesseract(pytesseract) -> None:
    env_dir = os.environ.get("Tesseract")  # your existing variable (a folder)
    candidates = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        os.path.join(env_dir, "tesseract.exe") if env_dir else None,
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            pytesseract.pytesseract.tesseract_cmd = c
            return

def ocr_pil_image(img: Image.Image) -> str:
    try:
        import pytesseract
        _configure_tesseract(pytesseract)
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pytesseract is not installed. Run: pip install pytesseract") from exc
    img = ImageOps.exif_transpose(img).convert("L")
    if max(img.size) < 1600:  # Tesseract works best around 300 DPI
        factor = 1600 / max(img.size)
        img = img.resize((int(img.width * factor), int(img.height * factor)))
    img = ImageOps.autocontrast(img)
    try:
        return pytesseract.image_to_string(img, config="--psm 6")
    except pytesseract.TesseractNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "The Tesseract program is not installed. Install it first:\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  macOS:   brew install tesseract\n"
            "  Ubuntu:  sudo apt install tesseract-ocr"
        ) from exc


def read_image(path: str | Path) -> str:
    with Image.open(path) as img:
        return ocr_pil_image(img)

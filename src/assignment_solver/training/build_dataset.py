"""Build data/processed/train.jsonl from solved DOCX and PDF assignments."""
from __future__ import annotations

import json
from pathlib import Path

from .docx_to_blocks import parse_solved_docx
from .pdf_to_blocks import parse_solved_pdf


def build_dataset(raw_dir: str | Path, out_path: str | Path) -> int:
    raw_dir, out_path = Path(raw_dir), Path(out_path)
    files = sorted(
        (
            p for p in raw_dir.iterdir()
            if p.suffix.lower() in {".docx", ".pdf"} and not p.name.startswith("~$")
        ),
        key=lambda p: p.name.lower(),
    ) if raw_dir.is_dir() else []
    if not files:
        raise FileNotFoundError(
            f"No .docx or .pdf files found in {raw_dir}. Put your solved assignments there."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for f in files:
            parsed = parse_solved_pdf(f) if f.suffix.lower() == ".pdf" else parse_solved_docx(f)
            for item in parsed["items"]:
                row = {
                    "instruction": item["question"],
                    "output": {"blocks": item["blocks"]},
                    "source": f.name,
                    "assignment": parsed["assignment"],
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
    return count


def load_dataset(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

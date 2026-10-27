"""End to end: input file -> solved .docx."""
from __future__ import annotations

import re
import tempfile
from datetime import datetime
from pathlib import Path

from .generate.llm import OllamaClient
from .generate.solver import attach_real_execution, generate_blocks
from .ingest import load_text
from .parsing import split_questions
from .render import render_assignment
from .retrieval import load_index


def default_title(path: Path) -> str:
    name = re.sub(r"[_\-]+", " ", path.stem).strip()
    return name.title() if name else "Assignment"


def extract_questions(input_path: str | Path) -> list[str]:
    return split_questions(load_text(input_path))


def solve_file(input_path: str | Path, cfg: dict, *, title: str | None = None,
               out_path: str | Path | None = None, run_code_blocks: bool | None = None,
               progress=print) -> tuple[Path, dict[int, list[str]]]:
    """Returns (output_path, {question_number: [warnings]})."""
    input_path = Path(input_path)
    questions = extract_questions(input_path)
    if not questions:
        raise ValueError(f"No text could be read from {input_path}")
    client = OllamaClient(cfg)
    index = load_index(cfg["paths"]["index"])
    run_code_blocks = cfg["code_execution"]["enabled"] if run_code_blocks is None else run_code_blocks

    items, all_warnings = [], {}
    with tempfile.TemporaryDirectory() as work:
        for n, q in enumerate(questions, start=1):
            progress(f"[{n}/{len(questions)}] {q[:70].replace(chr(10), ' ')}...")
            blocks, warns = generate_blocks(q, client, cfg, index)
            if run_code_blocks:
                blocks, more = attach_real_execution(blocks, cfg, Path(work) / f"q{n}")
                warns += more
            items.append({"question": q, "blocks": blocks})
            if warns:
                all_warnings[n] = warns
        if out_path is None:
            stamp = datetime.now().strftime("%d%m%Y")
            out_path = Path(cfg["paths"]["outputs"]) / f"{input_path.stem}_solved_{stamp}.docx"
        out = render_assignment(
            out_path,
            student_name=cfg["student"]["name"],
            email=cfg["student"]["email"],
            assignment_name=title or default_title(input_path),
            items=items,
        )
    return out, all_warnings

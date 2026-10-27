"""Turn a solved PDF into question and plain-text answer pairs."""
from __future__ import annotations

import re
from pathlib import Path

from ..ingest.pdf import read_pdf

_QUESTION = re.compile(r"^\s*Question\s*\d+\s*[:.)\-–]?\s*", re.I)
_ANSWER = re.compile(r"^\s*Answer\s*:\s*(.*)$", re.I)


def parse_solved_pdf(path: str | Path) -> dict:
    """Return solved PDF questions as paragraph blocks."""
    text = read_pdf(path)
    lines = text.replace("\r", "").splitlines()
    assignment = Path(path).stem
    items: list[dict] = []
    sections: list[list[str]] = []
    current: list[str] | None = None

    for line in lines:
        if _QUESTION.match(line):
            if current is not None:
                sections.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
        else:
            match = re.match(r"^\s*Assignment Name\s*:\s*(.*)$", line, re.I)
            if match and match.group(1).strip():
                assignment = match.group(1).strip()
    if current is not None:
        sections.append(current)

    for section in sections:
        question_match = _QUESTION.match(section[0])
        if question_match is None:
            continue
        question_parts = [section[0][question_match.end():].strip()]
        answer_lines: list[str] = []
        answer_found = False

        for line in section[1:]:
            answer_match = _ANSWER.match(line)
            if answer_match:
                answer_found = True
                answer_lines.append(answer_match.group(1))
            elif answer_found:
                answer_lines.append(line)
            elif line.strip():
                question_parts.append(line.strip())

        if not answer_found:
            answer_lines = question_parts[1:]
            question_parts = question_parts[:1]

        question = " ".join(part for part in question_parts if part)
        answer = " ".join(line.strip() for line in answer_lines if line.strip())
        if question and answer:
            items.append({
                "question": question,
                "blocks": [{"type": "paragraph", "text": answer}],
            })

    return {"assignment": assignment, "items": items}

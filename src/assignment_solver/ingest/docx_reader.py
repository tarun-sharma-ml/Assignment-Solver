"""DOCX reader that keeps paragraphs and tables in document order."""
from __future__ import annotations

from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_block_items(document):
    """Yield Paragraph and Table objects in the order they appear in the body."""
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def read_docx(path: str | Path) -> str:
    document = docx.Document(str(path))
    lines: list[str] = []
    for item in iter_block_items(document):
        if isinstance(item, Paragraph):
            lines.append(item.text)
        else:
            for row in item.rows:
                lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)

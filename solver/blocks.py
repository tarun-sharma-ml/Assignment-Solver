"""Parse the model's Markdown answer into simple typed blocks (easy to render, easy to annotate)."""
import re
from dataclasses import dataclass, field


@dataclass
class Block:
    kind: str                     # heading | para | bullet | number | table | code | output | image
    text: str = ""
    level: int = 3                # heading level
    lang: str = ""                # code language
    rows: list = field(default_factory=list)   # table rows (first row = header)
    n: int = 0                    # list number


FENCE = re.compile(r"^```\s*([\w+-]*)\s*$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_markdown(md: str) -> list[Block]:
    blocks: list[Block] = []
    lines = md.replace("\r\n", "\n").split("\n")
    i, para = 0, []

    def flush():
        if para:
            blocks.append(Block("para", " ".join(s.strip() for s in para)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        fence = FENCE.match(line.strip())
        if fence:
            flush()
            lang, code = fence.group(1).lower(), []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append(Block("code", "\n".join(code).rstrip(), lang=lang))
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            flush()
            rows = [_cells(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            blocks.append(Block("table", rows=rows))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush()
            blocks.append(Block("heading", m.group(2).strip(), level=len(m.group(1))))
        elif re.match(r"^\s*[-*•]\s+", line):
            flush()
            blocks.append(Block("bullet", re.sub(r"^\s*[-*•]\s+", "", line).strip()))
        elif re.match(r"^\s*\d+[.)]\s+", line):
            flush()
            mm = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
            blocks.append(Block("number", mm.group(2).strip(), n=int(mm.group(1))))
        elif not line.strip():
            flush()
        else:
            para.append(line)
        i += 1
    flush()
    return blocks

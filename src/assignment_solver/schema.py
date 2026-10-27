"""The JSON structure the model produces and the renderer consumes.

An answer is a list of *blocks*. Each block is a dict with a ``type``:

    paragraph : {"type": "paragraph", "text": str}
    heading   : {"type": "heading",   "text": str}               # bold label, e.g. "Limitations:"
    bullets   : {"type": "bullets",   "items": [str, ...]}
    table     : {"type": "table",     "rows": [[str, ...], ...]}   # row 0 is the header row
    code      : {"type": "code",      "text": str}               # code the student would run
    output    : {"type": "output",    "text": str}               # program output (monospace)
    figure    : {"type": "figure",    "caption": str, "path": str (optional, filled by runner)}
    example   : {"type": "example",   "text": str}               # "Example: ..." paragraph
"""
from __future__ import annotations

import json
import re
from typing import Any

BLOCK_TYPES = {"paragraph", "heading", "bullets", "table", "code", "output", "figure", "example"}

SCHEMA_DESCRIPTION = """Return ONLY a JSON object: {"blocks": [ ... ]}.
Each block is one of:
{"type":"paragraph","text":"..."}            explanation paragraph
{"type":"heading","text":"Limitations:"}     bold label that introduces what follows
{"type":"bullets","items":["...","..."]}     bullet list
{"type":"table","rows":[["Header 1","Header 2"],["cell","cell"]]}   first row is the header
{"type":"heading","text":"Python Code:"}     label placed right before a code block
{"type":"code","text":"python source"}       complete runnable code (never include its output)
{"type":"figure","caption":"Figure: ..."}    only if the code draws a plot
{"type":"example","text":"..."}              a short worked example, always last
Start with an introductory paragraph, use tables for comparisons, bullets for lists, and finish with an example."""


def _clean_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalise_block(block: Any) -> dict | None:
    """Coerce a model-produced block into a valid one, or return None to drop it."""
    if isinstance(block, str):
        return {"type": "paragraph", "text": block.strip()} if block.strip() else None
    if not isinstance(block, dict):
        return None
    kind = _clean_str(block.get("type")).lower()
    if kind not in BLOCK_TYPES:
        text = _clean_str(block.get("text"))
        return {"type": "paragraph", "text": text} if text else None

    if kind == "bullets":
        items = block.get("items") or []
        if isinstance(items, str):
            items = [items]
        items = [_clean_str(i) for i in items if _clean_str(i)]
        return {"type": "bullets", "items": items} if items else None
    if kind == "table":
        rows = block.get("rows") or []
        rows = [[_clean_str(c) for c in row] for row in rows if isinstance(row, list) and row]
        if len(rows) < 1:
            return None
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        return {"type": "table", "rows": rows}
    if kind == "figure":
        out = {"type": "figure", "caption": _clean_str(block.get("caption")) or "Figure"}
        if block.get("path"):
            out["path"] = str(block["path"])
        return out
    text = block.get("text")
    if kind in ("code", "output"):
        text = "" if text is None else str(text).strip("\n")
        return {"type": kind, "text": text} if text.strip() else None
    text = _clean_str(text)
    return {"type": kind, "text": text} if text else None


def normalise_blocks(blocks: Any) -> list[dict]:
    if not isinstance(blocks, list):
        return []
    return [nb for nb in (normalise_block(b) for b in blocks) if nb]


def parse_model_json(raw: str) -> list[dict]:
    """Extract ``{"blocks": [...]}`` from raw model text, tolerating code fences and noise."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    candidates = [text]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            data = data.get("blocks", [])
        blocks = normalise_blocks(data)
        if blocks:
            return blocks
    raise ValueError("Model output was not valid block JSON")

"""Solve each question: LLM answer -> parse -> run code -> (fix on failure) -> cache."""
import hashlib
import json
import re
from pathlib import Path

from .blocks import Block, parse_markdown, strip_echo
from .code_runner import run_python
from .pdf_parser import Question
from .prompts import SYSTEM_PROMPT, fix_prompt, user_prompt

CACHE_DIR = Path(".cache")
CODE_ASKED = re.compile(r"\b(code|snippet|program|script|yaml|dockerfile|command|config|configuration|syntax|implement)\b", re.I)


def code_not_wanted(q: Question) -> bool:
    return q.kind == "theory" and not CODE_ASKED.search(q.text)


def drop_code(blocks):
    """Last resort: remove code/output/figures and any 'Example: ... following code ...' lead-in."""
    keep = []
    for b in blocks:
        if b.kind in ("code", "output", "image"):
            continue
        if b.kind == "para" and b.text.lower().startswith("example") and re.search(r"\bcode\b", b.text, re.I):
            continue
        keep.append(b)
    return keep


def _key(model, run_code, prompt):
    """Cache key covers the model AND the exact prompts, so editing prompts invalidates old answers."""
    raw = f"{model}|{run_code}|{SYSTEM_PROMPT}|{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _dump(blocks):
    return [b.__dict__ for b in blocks]


def _load(data):
    return [Block(**d) for d in data]


def annotate_with_output(blocks, fig_dir: Path):
    """Run each ```python block; insert real output / figures after it.
    Returns (new_blocks, first_recoverable_error or None)."""
    out, error = [], None
    for b in blocks:
        out.append(b)
        if b.kind != "code" or b.lang not in ("python", "py"):
            continue
        res = run_python(b.text, fig_dir)
        if res.skipped:
            print(f"      code not executed: {res.skipped}")
        elif not res.ok:
            error = error or res.error
            print(f"      code error: {res.error.strip().splitlines()[-1][:120]}")
        else:
            if res.stdout:
                out.append(Block("output", res.stdout))
            for img in res.images or []:
                out.append(Block("image", img))
    return out, error


def solve_question(client, q: Question, marks: int, run_code=True, max_fix=2, out_dir=Path("output"),
                   examples_text: str = ""):
    CACHE_DIR.mkdir(exist_ok=True)
    prompt = user_prompt(q.text, marks, q.kind, examples_text)
    cache_file = CACHE_DIR / f"{_key(client.model, run_code, prompt)}.json"
    if cache_file.exists():
        print("      (cached)")
        return _load(json.loads(cache_file.read_text(encoding="utf-8")))

    messages = [{"role": "user", "content": prompt}]
    md = client.complete(messages)
    blocks = strip_echo(parse_markdown(md), q.text)
    fig_dir = out_dir / "figures" / f"q{q.number}"

    if code_not_wanted(q) and any(b.kind == "code" for b in blocks):
        print("      theory question but the model added code; asking for a code-free rewrite")
        messages += [{"role": "assistant", "content": md},
                     {"role": "user", "content": "This is a theory question that does not ask for code. Rewrite the "
                      "FULL answer with NO code blocks at all. Keep the tables and give a non-code example."}]
        md = client.complete(messages)
        blocks = strip_echo(parse_markdown(md), q.text)
        if any(b.kind == "code" for b in blocks):
            blocks = drop_code(blocks)

    if run_code and any(b.kind == "code" and b.lang in ("python", "py") for b in blocks):
        for attempt in range(max_fix + 1):
            annotated, error = annotate_with_output(blocks, fig_dir)
            if not error or attempt == max_fix:
                blocks = annotated
                if error:
                    print("      WARNING: code still failing after fixes; review this answer manually")
                break
            print(f"      asking the model to fix the code (attempt {attempt + 1}/{max_fix})")
            messages += [{"role": "assistant", "content": md},
                         {"role": "user", "content": fix_prompt(error)}]
            md = client.complete(messages)
            blocks = strip_echo(parse_markdown(md), q.text)

    cache_file.write_text(json.dumps(_dump(blocks)), encoding="utf-8")
    return blocks
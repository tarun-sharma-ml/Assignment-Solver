"""Question -> list of blocks, using retrieval + the local model + real code execution."""
from __future__ import annotations

from pathlib import Path

from ..retrieval import search
from ..schema import parse_model_json
from .code_runner import run_code
from .llm import OllamaClient
from .prompt import inference_messages


def generate_blocks(question: str, client: OllamaClient, cfg: dict, index: dict | None) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    examples = search(index, question, k=cfg["retrieval"]["top_k"])
    messages = inference_messages(question, examples, cfg["retrieval"]["max_example_chars"])
    raw = ""
    for attempt in range(3):
        raw = client.chat_json(messages)
        try:
            blocks = parse_model_json(raw)
            break
        except ValueError:
            warnings.append(f"model returned invalid JSON (attempt {attempt + 1})")
    else:
        warnings.append("could not parse model output; inserted raw text - please rewrite this answer")
        blocks = [{"type": "paragraph", "text": raw.strip() or "(no answer generated)"}]
    if not any(b["type"] == "example" for b in blocks):
        warnings.append("answer has no Example block")
    if not examples:
        warnings.append("no similar earlier answer found - style may be less accurate")
    return blocks, warnings


def attach_real_execution(blocks: list[dict], cfg: dict, workdir: str | Path) -> tuple[list[dict], list[str]]:
    """Replace any model-invented output with the output of actually running the code."""
    warnings: list[str] = []
    timeout = cfg["code_execution"]["timeout_seconds"]
    # drop output the model made up, plus its "Output:" label and invented figures
    cleaned: list[dict] = []
    for b in blocks:
        if b["type"] == "output":
            continue
        if b["type"] == "heading" and b["text"].strip().lower().startswith("output"):
            continue
        cleaned.append(b)
    has_code = any(b["type"] == "code" for b in cleaned)
    if not has_code:
        return [b for b in cleaned if b["type"] != "figure"], warnings

    result_blocks: list[dict] = []
    pending_figures = [b for b in cleaned if b["type"] == "figure"]
    for b in cleaned:
        if b["type"] == "figure":
            continue  # re-inserted right after the code that produced the image
        result_blocks.append(b)
        if b["type"] != "code":
            continue
        res = run_code(b["text"], workdir, timeout)
        if res.skipped_reason:
            if res.skipped_reason != "shell commands":
                warnings.append(f"code not executed ({res.skipped_reason})")
            continue
        if not res.ok:
            warnings.append(f"code failed to run: {res.error.splitlines()[-1] if res.error else 'unknown error'}")
        if res.stdout.strip():
            result_blocks.append({"type": "heading", "text": "Output:"})
            result_blocks.append({"type": "output", "text": res.stdout})
        for path in res.images:
            fig = pending_figures.pop(0) if pending_figures else {"type": "figure", "caption": "Figure: Generated plot"}
            result_blocks.append({**fig, "path": path})
    return result_blocks, warnings

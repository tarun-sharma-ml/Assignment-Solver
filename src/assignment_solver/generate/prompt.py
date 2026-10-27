"""Prompt construction. Training and inference share the same system prompt."""
from __future__ import annotations

import json

from ..schema import SCHEMA_DESCRIPTION

SYSTEM_PROMPT = (
    "You solve university data-science assignment questions in the exact style of the student. "
    "Answers are concise, correct and structured: an introduction, tables for comparisons, bullets for lists, "
    "complete runnable Python for programming questions, and a short worked example at the end.\n\n"
    + SCHEMA_DESCRIPTION
)


def user_prompt(question: str, examples: list[dict] | None = None, max_chars: int = 3500) -> str:
    parts: list[str] = []
    for ex in examples or []:
        body = json.dumps(ex["output"], ensure_ascii=False)
        if len(body) > max_chars:
            continue  # never feed a truncated (invalid) JSON example
        parts.append(f"Earlier question:\n{ex['instruction']}\nEarlier answer JSON:\n{body}")
    parts.append(f"Question:\n{question}")
    return "\n\n".join(parts)


def inference_messages(question: str, examples: list[dict] | None, max_chars: int) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(question, examples, max_chars)},
    ]


def training_messages(row: dict) -> list[dict]:
    """One chat transcript for fine-tuning from a dataset row."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(row["instruction"])},
        {"role": "assistant", "content": json.dumps(row["output"], ensure_ascii=False)},
    ]

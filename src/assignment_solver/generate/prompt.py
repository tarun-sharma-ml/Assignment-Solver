"""Prompt construction. Training and inference share the same system prompt."""
from __future__ import annotations

import json

from ..schema import SCHEMA_DESCRIPTION

SYSTEM_PROMPT = (
    "You solve university assignment questions accurately and in a clear, professional academic style. "
    "Answer every part of the current question directly. Keep the response concise but sufficiently detailed "
    "to explain the reasoning. Do not add a generic introduction, conclusion, or unrelated example. "
    "Use separate blocks instead of putting a multi-part answer in one long paragraph: use a table for "
    "comparisons, bullets for lists, and a code block for requested SQL or programming code. "
    "Check definitions, examples, calculations, and code for internal consistency before answering. "
    "Do not invent query results or claim code has been run.\n\n"
    + SCHEMA_DESCRIPTION
)


def user_prompt(question: str, examples: list[dict] | None = None, max_chars: int = 3500) -> str:
    parts: list[str] = []
    if examples:
        parts.append(
            "The earlier answers below are style references only. Solve the current question independently; "
            "do not copy their facts, examples, or mistakes."
        )
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

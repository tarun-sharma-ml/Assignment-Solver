"""Load config.yaml with sensible defaults."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "student": {"name": "Your Name", "email": "you@example.com"},
    "model": {
        "name": "assignment-solver",
        "fallback": "qwen2.5:3b-instruct",
        "host": "http://localhost:11434",
        "temperature": 0.3,
        "num_ctx": 6144,
        "num_predict": 1800,
        "timeout_seconds": 900,
    },
    "retrieval": {"top_k": 2, "max_example_chars": 3500},
    "code_execution": {"enabled": True, "timeout_seconds": 60},
    "paths": {
        "raw_assignments": "data/raw_assignments",
        "dataset": "data/processed/train.jsonl",
        "index": "data/processed/index.joblib",
        "outputs": "outputs",
    },
}


def _merge(base: dict, extra: dict) -> dict:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = copy.deepcopy(DEFAULTS)
    candidate = Path(path) if path else Path("config.yaml")
    if candidate.exists():
        with open(candidate, "r", encoding="utf-8") as fh:
            _merge(cfg, yaml.safe_load(fh) or {})
    elif path:
        raise FileNotFoundError(f"Config file not found: {path}")
    return cfg

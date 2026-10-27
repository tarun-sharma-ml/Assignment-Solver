"""TF-IDF retrieval over the student's earlier questions (free, no GPU, no downloads)."""
from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from ..training.build_dataset import load_dataset


def build_index(dataset_path: str | Path, index_path: str | Path) -> int:
    rows = load_dataset(dataset_path)
    if not rows:
        raise ValueError("Dataset is empty - run `assignment-solver build-dataset` first.")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
    matrix = vectorizer.fit_transform([r["instruction"] for r in rows])
    Path(index_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "rows": rows}, index_path)
    return len(rows)


def load_index(index_path: str | Path) -> dict | None:
    p = Path(index_path)
    return joblib.load(p) if p.exists() else None


def search(index: dict | None, question: str, k: int = 2, min_score: float = 0.08) -> list[dict]:
    """Return up to k earlier rows most similar to ``question``."""
    if not index:
        return []
    vec = index["vectorizer"].transform([question])
    scores = linear_kernel(vec, index["matrix"]).ravel()
    order = scores.argsort()[::-1][:k]
    return [index["rows"][i] for i in order if scores[i] >= min_score]

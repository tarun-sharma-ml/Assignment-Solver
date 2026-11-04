"""Learn from your own solved assignments (few-shot retrieval; no model training needed).

Put solved assignments (.docx / .pdf / .md / .txt) in the examples/ folder. Each file should contain
"Question N: ... Answer: ..." pairs. For every new question the most similar past answers are
retrieved and shown to the model so it copies your depth, structure, tone and formatting.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

QUESTION_RE = re.compile(r"(?im)^\s*Question\s*(\d+)\s*[:.\-)]?\s*")
ANSWER_RE = re.compile(r"(?im)^\s*Answer\s*:?\s*")
STOP = set("the and for with that this from are was were what how why does did can you your which when "
           "into about between their them they then than such also its not but has have had will would "
           "should could explain write python program question answer use using".split())


@dataclass
class Example:
    question: str
    answer: str
    source: str


# ---------- reading files ----------
def _is_code_par(p) -> bool:
    runs = [r for r in p.runs if r.text.strip()]
    return bool(runs) and all((r.font.name or "").lower().startswith(("courier", "consolas")) for r in runs)


def read_docx(path: Path) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc, out, in_code = Document(str(path)), [], False
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            p = Paragraph(child, doc)
            code = _is_code_par(p)
            if code and not in_code:
                out.append("```python")
            if in_code and not code:
                out.append("```")
            in_code = code
            out.append(p.text)
        elif tag == "tbl":
            if in_code:
                out.append("```"); in_code = False
            rows = [[c.text.strip().replace("\n", " ") for c in r.cells] for r in Table(child, doc).rows]
            if rows:
                out.append("| " + " | ".join(rows[0]) + " |")
                out.append("|" + "---|" * len(rows[0]))
                out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    if in_code:
        out.append("```")
    return "\n".join(out)


def read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        return read_docx(path)
    if ext == ".pdf":
        from .pdf_parser import read_pdf_text
        return read_pdf_text(path)
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def parse_pairs(text: str, source: str) -> list[Example]:
    matches = list(QUESTION_RE.finditer(text))
    pairs = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.end():end]
        a = ANSWER_RE.search(chunk)
        if not a:
            continue
        q = re.sub(r"\s+", " ", chunk[:a.start()]).strip()
        ans = chunk[a.end():].strip()
        if len(q) > 15 and len(ans) > 120:          # skip blank templates / empty answers
            pairs.append(Example(q, ans, source))
    return pairs


def load_examples(folder: str | Path) -> list[Example]:
    folder, examples = Path(folder), []
    if not folder.is_dir():
        return examples
    for f in sorted(folder.rglob("*")):
        if f.is_file() and f.suffix.lower() in (".docx", ".pdf", ".md", ".txt") and f.name.lower() != "readme.md":
            try:
                examples += parse_pairs(read_file(f), f.name)
            except Exception as e:
                print(f"   could not read {f.name}: {type(e).__name__}: {e}")
    return examples


# ---------- retrieval (pure-Python TF-IDF, no extra dependencies) ----------
def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z0-9+#_-]{2,}", text.lower()) if w not in STOP]


class ExampleIndex:
    def __init__(self, examples: list[Example]):
        self.examples = examples
        docs = [Counter(_tokens(e.question + " " + e.answer[:1500])) for e in examples]
        n = len(docs)
        df = Counter(t for d in docs for t in d)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, counts: Counter):
        v = {t: (1 + math.log(c)) * self.idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def retrieve(self, question: str, k: int = 2, min_score: float = 0.05) -> list[Example]:
        if not self.examples:
            return []
        q = self._vec(Counter(_tokens(question)))
        scored = sorted(((sum(w * v.get(t, 0) for t, w in q.items()), e)
                         for v, e in zip(self.vecs, self.examples)), key=lambda x: -x[0])
        return [e for s, e in scored[:k] if s >= min_score]


def format_examples(examples: list[Example], max_chars: int = 2800) -> str:
    """Text block inserted into the prompt."""
    parts = []
    for i, e in enumerate(examples, 1):
        ans = e.answer if len(e.answer) <= max_chars else e.answer[:max_chars].rsplit("\n", 1)[0] + "\n[...]"
        parts.append(f"--- Example {i} (from the student's earlier work: {e.source}) ---\n"
                     f"Question: {e.question}\nAnswer:\n{ans}")
    return "\n\n".join(parts)

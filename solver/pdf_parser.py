"""Extract questions from an assignment PDF (or a plain text file)."""
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

# Lines that are page furniture and never part of a question.
NOISE_PATTERNS = [
    r"^\s*\d{1,3}\s*$",                      # lone page numbers
    r"^\s*(java \+ dsa\s*)?pwskills\s*$",    # footers
    r"^\s*answer\s*:?\s*$",                  # empty "Answer:" labels
    r"^\s*skills\s*$",                       # logo text
]
NOISE_RE = [re.compile(p, re.I) for p in NOISE_PATTERNS]

QUESTION_RE = re.compile(r"(?im)^\s*Question\s*(\d+)\s*[:.\-)]?\s*")
NUMBERED_RE = re.compile(r"(?m)^\s*(\d{1,3})[.)]\s+(?=[A-Z])")

CODE_HINTS = re.compile(
    r"\b(write|create|implement|build|develop)\b.{0,60}\b(python|program|code|script|dockerfile|"
    r"function|snippet|class)\b|\b(python program|python code|include your python code)\b|"
    r"\b(plot|visuali[sz]e|print the)\b",
    re.I | re.S,
)


@dataclass
class Question:
    number: int
    text: str
    kind: str = "theory"          # "theory" or "practical"


def read_pdf_text(path: Path) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def clean(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not any(r.match(ln) for r in NOISE_RE)]
    return "\n".join(lines)


def detect_marks(text: str, default: int = 20) -> int:
    m = re.search(r"each question carries\s+(\d+)\s+marks", text, re.I)
    return int(m.group(1)) if m else default


def _readability(s: str) -> float:
    """Share of alphabetic words with 3+ letters that contain a vowel.
    Used to drop garbled duplicate text layers some PDFs contain."""
    words = re.findall(r"[A-Za-z]{3,}", s)
    if not words:
        return 0.0
    return sum(1 for w in words if re.search(r"[aeiouyAEIOUY]", w)) / len(words)


def _split(text: str, regex: re.Pattern):
    matches = list(regex.finditer(text))
    items = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = re.sub(r"\s+", " ", text[m.end():end]).strip()
        if body:
            items.append((int(m.group(1)), body))
    return items


def _split_unnumbered(text: str):
    """For PDFs whose list numbers are not in the text layer (auto-numbered lists).
    A new question starts at a capitalised line when the previous line ended a
    sentence (terminal punctuation or trailing space). Questions are numbered 1..N."""
    items, current, prev_ended = [], [], True
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            prev_ended = True
            continue
        if line.endswith(":") and len(line.split()) <= 4:   # section headers
            prev_ended = True
            continue
        if len(line.split()) <= 4 and any(re.match(r"^[a-z]+[A-Z][a-z]*[A-Z]", t) for t in line.split()):
            continue                                        # garbled text-layer debris
        starts_new = prev_ended and line[0].isupper()
        if starts_new and current:
            items.append(" ".join(current))
            current = []
        current.append(line)
        prev_ended = raw.endswith(" ") or line.endswith(("?", ".", ":"))
    if current:
        items.append(" ".join(current))
    items = [re.sub(r"\s+", " ", i).strip() for i in items]
    items = [i for i in items if len(i.split()) >= 4 and _readability(i) > 0.9]
    return [(n, body) for n, body in enumerate(items, start=1)]


def classify(text: str) -> str:
    return "practical" if CODE_HINTS.search(text) else "theory"


def parse_questions(text: str) -> list[Question]:
    text = clean(text)
    items = _split(text, QUESTION_RE)
    if len(items) < 2:                       # fall back to "1. ...", "2. ..." lists
        items = _split(text, NUMBERED_RE)
    if len(items) < 2:                       # fall back to auto-numbered lists
        items = _split_unnumbered(text)

    # keep the best (most readable) candidate per question number, then sort
    best: dict[int, str] = {}
    for num, body in items:
        if num not in best or _readability(body) > _readability(best[num]) + 0.05:
            best[num] = body
    questions = [Question(n, b, classify(b)) for n, b in sorted(best.items())]
    return questions


def load_questions(path: str) -> tuple[list[Question], int]:
    """Return (questions, marks_per_question) from a .pdf or .txt/.md file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    raw = read_pdf_text(p) if p.suffix.lower() == ".pdf" else p.read_text(encoding="utf-8")
    marks = detect_marks(raw)
    questions = parse_questions(raw)
    if not questions:
        raise ValueError(
            "No questions found. Make sure questions look like 'Question 1: ...' or '1. ...', "
            "or pass a .txt file with one question per numbered line."
        )
    return questions, marks

"""Split raw assignment text into individual questions."""
from __future__ import annotations

import re

# "Question 1:", "Q1.", "Q.2)" and top-level numbered items like "1.", "2)", "(3)".
# Nested list markers such as "  2." are intentionally ignored so they don't split a question.
_QUESTION_START = re.compile(
    r"^\s*(?:question|ques|q)\s*\.?\s*(?P<n1>\d{1,3})\s*[:.)\-–]?\s*",
    re.IGNORECASE,
)
_BARE_START = re.compile(r"^(?P<n2>\d{1,3})\s*[.)]|^\((?P<n3>\d{1,3})\)", re.IGNORECASE)


def _clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_questions(text: str) -> list[str]:
    """Return question texts (numbering prefix removed).

    Numbers must increase (1, 2, 3 ...) so stray numbered lists inside a
    question are not mistaken for new questions. With no numbering found the
    whole text is one question.
    """
    lines = text.replace("\r", "").split("\n")
    starts: list[tuple[int, int, int]] = []
    expected = 1
    for idx, line in enumerate(lines):
        m = _QUESTION_START.match(line)
        if m:
            number = int(m.group("n1"))
        elif line and not line[0].isspace() and (m := _BARE_START.match(line)):
            number = int(m.group("n2") or m.group("n3"))
        else:
            continue

        if number == expected or (not starts and number in (0, 1)):
            starts.append((idx, number, m.end()))
            expected = number + 1

    if not starts:
        cleaned = _clean(text)
        return [cleaned] if cleaned else []

    questions: list[str] = []
    for i, (line_idx, _num, prefix_len) in enumerate(starts):
        end_idx = starts[i + 1][0] if i + 1 < len(starts) else len(lines)
        chunk = [lines[line_idx][prefix_len:]] + lines[line_idx + 1 : end_idx]
        question = _clean("\n".join(chunk))
        question = re.sub(r"\s*Answer\s*:?\s*$", "", question, flags=re.I).strip()
        if question:
            questions.append(question)

    return questions

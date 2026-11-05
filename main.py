#!/usr/bin/env python3
"""Assignment Solver: assignment PDF -> answers (Gemini) -> formatted Word document.

Examples:
  python main.py assignment.pdf --list                    # only show the parsed questions
  python main.py assignment.pdf --marks 20 --out answers.docx
  python main.py assignment.pdf --only 1,3,6-8 --marks 10
  python main.py assignment.pdf --dry-run                 # test the pipeline without an API key
"""
import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from solver.docx_builder import AnswerDocument
from solver.examples import ExampleIndex, format_examples, load_examples
from solver.llm import GeminiClient, MockClient
from solver.pdf_parser import load_questions
from solver.pipeline import solve_question


def nice_title(stem: str) -> str:
    """'mlflow_deployment_monitoring_assignment_pdf_04112026' -> 'Mlflow Deployment Monitoring'"""
    words = [w for w in stem.replace("-", "_").split("_")
             if w and not w.isdigit() and w.lower() not in {"pdf", "assignment", "docx", "final"}]
    return (" ".join(words) or stem).title()


def parse_only(spec: str | None, available: set[int]) -> set[int]:
    if not spec:
        return available
    chosen = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            chosen.update(range(int(a), int(b) + 1))
        elif part:
            chosen.add(int(part))
    return chosen & available


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="Solve assignment questions and export a Word document.")
    ap.add_argument("input", help="assignment .pdf (or .txt with numbered questions)")
    ap.add_argument("--out", default=None, help="output .docx (default: output/<input name>_answers.docx)")
    ap.add_argument("--marks", type=int, default=None, help="marks per question (auto-detected from the PDF if omitted)")
    ap.add_argument("--only", default=None, help="solve only these questions, e.g. 1,3,6-8")
    ap.add_argument("--title", default=None, help="document title")
    ap.add_argument("--name", default="", help="student name to show on the first page")
    ap.add_argument("--model", default=None, help="Gemini model id (default: GEMINI_MODEL env or gemini-3.5-flash-lite)")
    ap.add_argument("--fallback-model", default=None, help="model to use if the main one stays overloaded (e.g. gemini-3.5-flash)")
    ap.add_argument("--delay", type=float, default=0, help="seconds to pause between questions (helps with rate limits)")
    ap.add_argument("--no-run-code", action="store_true", help="do not execute generated Python code")
    ap.add_argument("--max-fix", type=int, default=2, help="max auto-fix attempts for failing code")
    ap.add_argument("--examples", default="examples", help="folder with your solved assignments to learn style from")
    ap.add_argument("--shots", type=int, default=2, help="how many similar past answers to show the model (0 = off)")
    ap.add_argument("--list-examples", action="store_true", help="show what was learned from the examples folder and exit")
    ap.add_argument("--list", action="store_true", help="only list the parsed questions and exit")
    ap.add_argument("--dry-run", action="store_true", help="use a mock model (no API key, no cost)")
    args = ap.parse_args()

    learned = load_examples(args.examples) if args.shots > 0 or args.list_examples else []
    if args.list_examples:
        print(f"Learned {len(learned)} solved question(s) from '{args.examples}/':")
        for e in learned:
            print(f"  [{e.source}] {e.question[:90]}  ({len(e.answer)} chars)")
        return
    index = ExampleIndex(learned) if learned and args.shots > 0 else None
    if index:
        print(f"Learning from {len(learned)} solved question(s) in '{args.examples}/' (using {args.shots} per question).")

    questions, detected = load_questions(args.input)
    marks = args.marks or detected
    selected = parse_only(args.only, {q.number for q in questions})
    questions = [q for q in questions if q.number in selected]

    print(f"Found {len(questions)} question(s), {marks} marks each "
          f"({sum(q.kind == 'practical' for q in questions)} practical).")
    if args.list:
        for q in questions:
            print(f"  Q{q.number:<3} [{q.kind:<9}] {q.text[:100]}")
        return

    client = MockClient() if args.dry_run else GeminiClient(model=args.model, fallback_model=args.fallback_model)
    run_code = not args.no_run_code
    if run_code:
        print("Note: generated Python code will be executed locally (see README, Security).")

    stem = Path(args.input).stem
    out_path = Path(args.out) if args.out else Path("output") / f"{stem}_answers.docx"
    doc = AnswerDocument(title=args.title or f"{nice_title(stem)} - Assignment Solutions",
                         subtitle=f"Each question carries {marks} marks", student=args.name)

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] Q{q.number} ({q.kind})")
        try:
            shots = format_examples(index.retrieve(q.text, k=args.shots)) if index else ""
            blocks = solve_question(client, q, marks, run_code=run_code, max_fix=args.max_fix,
                                    out_dir=out_path.parent, examples_text=shots)
        except Exception as e:                       # keep going; one failure must not lose the rest
            print(f"      FAILED: {type(e).__name__}: {e}")
            continue
        doc.add_question(q.number, q.text)
        doc.add_blocks(blocks)
        doc.save(out_path)                           # save after every question (crash-safe)
        if args.delay and i < len(questions):
            time.sleep(args.delay)

    doc.save(out_path)
    print(f"\nDone. Saved: {out_path}")


if __name__ == "__main__":
    sys.exit(main())
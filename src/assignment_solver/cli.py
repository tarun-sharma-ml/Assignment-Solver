"""Command line interface:  assignment-solver <command>"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="assignment-solver", description=__doc__)
    ap.add_argument("--config", default=None, help="path to config.yaml (default: ./config.yaml)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "build-dataset",
        help="turn your solved .docx and .pdf files into the training dataset and retrieval index",
    )

    p = sub.add_parser("questions", help="show how an input file is split into questions (no AI used)")
    p.add_argument("input")

    p = sub.add_parser("solve", help="solve an assignment file into a .docx")
    p.add_argument("input", help="pdf, docx, image or text file")
    p.add_argument("-o", "--output", default=None)
    p.add_argument("-t", "--title", default=None, help="Assignment Name shown in the header")
    p.add_argument("--no-run", action="store_true", help="do not execute the generated code")

    args = ap.parse_args(argv)
    cfg = load_config(args.config)

    if args.cmd == "build-dataset":
        from .retrieval import build_index
        from .training.build_dataset import build_dataset

        n = build_dataset(cfg["paths"]["raw_assignments"], cfg["paths"]["dataset"])
        print(f"Wrote {n} training pairs to {cfg['paths']['dataset']}")
        build_index(cfg["paths"]["dataset"], cfg["paths"]["index"])
        print(f"Built retrieval index at {cfg['paths']['index']}")
        return 0

    if args.cmd == "questions":
        from .pipeline import extract_questions

        for i, q in enumerate(extract_questions(args.input), start=1):
            print(f"--- Question {i}\n{q}\n")
        return 0

    if args.cmd == "solve":
        from .generate.llm import OllamaError
        from .pipeline import solve_file

        try:
            out, warnings = solve_file(
                args.input, cfg, title=args.title, out_path=args.output, run_code_blocks=False if args.no_run else None
            )
        except (OllamaError, ValueError, FileNotFoundError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"\nSaved: {out}")
        if warnings:
            print("\nCheck these before submitting:")
            for n, items in warnings.items():
                for w in items:
                    print(f"  Q{n}: {w}")
        print("\nAlways read the answers yourself - small models can be wrong.")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

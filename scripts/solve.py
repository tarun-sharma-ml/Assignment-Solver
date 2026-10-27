"""Run without installing:  python scripts/solve.py data/inputs/my_assignment.pdf"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from assignment_solver.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["solve", *sys.argv[1:]]))

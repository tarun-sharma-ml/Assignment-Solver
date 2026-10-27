"""Run the Python the model wrote and capture REAL output and figures.

Safety: code runs in a throw-away temp directory in a separate process with a
timeout. It is NOT a hard sandbox - obviously destructive code is refused, but you
should still read what the model wrote. Disable with `code_execution.enabled: false`.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PREAMBLE = '''\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as _plt
import atexit as _atexit, itertools as _it
_counter = _it.count(1)
def _save_all():
    for _num in _plt.get_fignums():
        _plt.figure(_num).savefig(f"__fig_{next(_counter):02d}.png", dpi=150, bbox_inches="tight")
    _plt.close("all")
def _show(*a, **k):
    _save_all()
_plt.show = _show
_atexit.register(_save_all)
'''

_SHELL = re.compile(r"^\s*(pip3?|python3? -m|ollama|conda|apt(-get)?|git|curl|cd|!|\$|%)", re.I)
_DANGEROUS = re.compile(r"shutil\.rmtree|os\.remove|os\.rmdir|os\.system|subprocess|__import__\(|rm -rf|os\.unlink", re.I)
_SQL = re.compile(r"^\s*(select|with|create|insert|update|delete|alter|drop|use|show)\b", re.I)

@dataclass
class RunResult:
    ok: bool
    stdout: str = ""
    error: str = ""
    images: list[str] = field(default_factory=list)
    skipped_reason: str = ""

def looks_like_sql(code: str) -> bool:
    return bool(_SQL.match(code))

def looks_like_shell(code: str) -> bool:
    lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
    return bool(lines) and all(_SHELL.match(l) for l in lines)


def run_code(code: str, workdir: str | Path, timeout: int = 60, max_chars: int = 4000) -> RunResult:
    if looks_like_sql(code):
        return RunResult(ok=False, skipped_reason="shell commands")
    if looks_like_shell(code):
        return RunResult(ok=False, skipped_reason="shell commands")
    if _DANGEROUS.search(code):
        return RunResult(ok=False, skipped_reason="potentially destructive code")
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        script = Path(tmp) / "snippet.py"
        script.write_text(PREAMBLE + "\n" + code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(script)], cwd=tmp, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return RunResult(ok=False, error=f"timed out after {timeout}s")
        images: list[str] = []
        for img in sorted(Path(tmp).glob("__fig_*.png")):
            dest = workdir / f"fig_{len(list(workdir.glob('fig_*.png'))) + 1:03d}.png"
            dest.write_bytes(img.read_bytes())
            images.append(str(dest))
        out = proc.stdout.strip("\n")
        if len(out) > max_chars:
            out = out[:max_chars] + "\n... (truncated)"
        if proc.returncode != 0:
            return RunResult(ok=False, stdout=out, error=proc.stderr.strip()[-600:], images=images)
        return RunResult(ok=True, stdout=out, images=images)

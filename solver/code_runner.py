"""Run the Python code from an answer in a subprocess and capture real output (+ matplotlib figures).

SECURITY: this executes model-generated code on YOUR machine. A simple deny-list blocks the most
dangerous calls, but it is not a sandbox. For untrusted use, run the whole project inside Docker.
"""
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DENY = re.compile(
    r"os\.system|subprocess|shutil\.rmtree|os\.remove|os\.rmdir|rmtree|socket\.|requests\.|urllib|"
    r"__import__|eval\(|exec\(|open\([^)]*['\"][wa]|input\(|sys\.exit|pip install",
    re.I,
)

PRELUDE = '''
import os as _os, itertools as _it
try:
    import matplotlib as _mpl
    _mpl.use("Agg")
    import matplotlib.pyplot as _plt
    _c = _it.count(1)
    def _show(*a, **k):
        for _n in _plt.get_fignums():
            _plt.figure(_n).savefig(_os.path.join(r"%(out)s", "fig_%%d.png" %% next(_c)),
                                    dpi=100, bbox_inches="tight")
        _plt.close("all")
    _plt.show = _show
except Exception:
    pass
'''


@dataclass
class RunResult:
    ok: bool
    stdout: str = ""
    error: str = ""
    images: list = None
    skipped: str = ""             # reason if not executed
    recoverable: bool = False     # True -> ask the LLM to fix the code


def run_python(code: str, out_dir: Path, timeout: int = 120) -> RunResult:
    if DENY.search(code):
        return RunResult(False, skipped="blocked by safety deny-list")
    out_dir = Path(out_dir).resolve()          # absolute: the script runs in a temp cwd
    out_dir.mkdir(parents=True, exist_ok=True)
    before = set(out_dir.glob("fig_*.png"))
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "snippet.py"
        script.write_text(PRELUDE % {"out": str(out_dir)} + "\n" + code, encoding="utf-8")
        env = {**os.environ, "MPLBACKEND": "Agg", "PYTHONHASHSEED": "0",
               "MLFLOW_TRACKING_URI": "sqlite:///mlflow.db"}   # file store is unsupported in MLflow 3.x
        try:
            proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                                  timeout=timeout, cwd=tmp, env=env, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return RunResult(False, error=f"Timed out after {timeout}s", recoverable=True)
    new_imgs = sorted(set(out_dir.glob("fig_*.png")) - before)
    if proc.returncode != 0:
        err = proc.stderr.strip()
        if "ModuleNotFoundError" in err or "ImportError" in err:
            return RunResult(False, error=err, skipped="a required library is not installed here")
        return RunResult(False, error=err, recoverable=True)
    return RunResult(True, stdout=proc.stdout.strip(), images=[str(p) for p in new_imgs])

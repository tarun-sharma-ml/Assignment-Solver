from assignment_solver.generate.code_runner import run_code
from assignment_solver.generate.solver import attach_real_execution

CFG = {"code_execution": {"timeout_seconds": 30}}


def test_runs_and_captures_output(tmp_path):
    r = run_code("print(1+1)", tmp_path)
    assert r.ok and r.stdout == "2"


def test_captures_figure(tmp_path):
    code = "import matplotlib.pyplot as plt\nplt.plot([1,2,3])\nplt.show()\nprint('done')"
    r = run_code(code, tmp_path)
    assert r.ok and len(r.images) == 1


def test_shell_and_dangerous_skipped(tmp_path):
    assert run_code("pip install chromadb", tmp_path).skipped_reason == "shell commands"
    assert run_code("import shutil\nshutil.rmtree('x')", tmp_path).skipped_reason


def test_attach_replaces_invented_output(tmp_path):
    blocks = [{"type": "code", "text": "print('real')"}, {"type": "heading", "text": "Output:"},
              {"type": "output", "text": "made up"}]
    out, warns = attach_real_execution(blocks, CFG, tmp_path)
    assert [b["type"] for b in out] == ["code", "heading", "output"]
    assert out[-1]["text"] == "real" and not warns

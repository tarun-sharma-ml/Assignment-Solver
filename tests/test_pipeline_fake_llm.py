import json
import docx
from assignment_solver import pipeline
from assignment_solver.config import load_config


class FakeClient:
    def __init__(self, cfg): pass
    def chat_json(self, messages):
        return json.dumps({"blocks": [
            {"type": "paragraph", "text": "Answer text."},
            {"type": "heading", "text": "Python Code:"},
            {"type": "code", "text": "print('ok')"},
            {"type": "example", "text": "Tiny."}]})


def test_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "OllamaClient", FakeClient)
    src = tmp_path / "hw.txt"
    src.write_text("Question 1: What is X?\nQuestion 2: What is Y?")
    cfg = load_config()
    cfg["paths"]["index"] = str(tmp_path / "none.joblib")
    out, warns = pipeline.solve_file(src, cfg, out_path=tmp_path / "o.docx")
    text = "\n".join(p.text for p in docx.Document(str(out)).paragraphs)
    assert "Question 2: What is Y?" in text and "ok" in text and "Name: " in text

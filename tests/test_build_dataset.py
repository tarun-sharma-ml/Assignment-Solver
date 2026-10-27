import json

import fitz
from assignment_solver.render import render_assignment
from assignment_solver.training.build_dataset import build_dataset


def test_build_dataset_reads_docx_and_pdf(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    render_assignment(
        raw_dir / "sample.docx",
        student_name="Student",
        email="student@example.com",
        assignment_name="DOCX Assignment",
        items=[{"question": "What is X?", "blocks": [{"type": "paragraph", "text": "DOCX answer."}]}],
    )

    pdf_path = raw_dir / "sample.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Assignment Name: PDF Assignment")
    page.insert_text((72, 100), "Question 1: What is Y?")
    page.insert_text((72, 128), "Answer:")
    page.insert_text((72, 156), "PDF answer.")
    pdf.save(pdf_path)
    pdf.close()

    out_path = tmp_path / "processed" / "train.jsonl"
    assert build_dataset(raw_dir, out_path) == 2

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    by_source = {row["source"]: row for row in rows}
    assert by_source["sample.pdf"]["assignment"] == "PDF Assignment"
    assert by_source["sample.pdf"]["instruction"] == "What is Y?"
    assert by_source["sample.pdf"]["output"]["blocks"] == [
        {"type": "paragraph", "text": "PDF answer."}
    ]
    assert by_source["sample.docx"]["output"]["blocks"][0]["text"] == "DOCX answer."

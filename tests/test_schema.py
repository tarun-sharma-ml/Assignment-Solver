import pytest
from assignment_solver.schema import normalise_block, parse_model_json


def test_parse_fenced_json():
    raw = '```json\n{"blocks":[{"type":"paragraph","text":"hi"}]}\n```'
    assert parse_model_json(raw) == [{"type": "paragraph", "text": "hi"}]


def test_table_is_padded():
    b = normalise_block({"type": "table", "rows": [["a", "b"], ["c"]]})
    assert b["rows"] == [["a", "b"], ["c", ""]]


def test_invalid_raises():
    with pytest.raises(ValueError):
        parse_model_json("not json")

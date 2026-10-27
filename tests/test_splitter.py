from assignment_solver.parsing import split_questions


def test_numbered_questions():
    text = "Question 1: What is AI?\nExplain.\nQuestion 2: Define ML.\n"
    qs = split_questions(text)
    assert len(qs) == 2 and qs[0].startswith("What is AI?") and qs[1] == "Define ML."


def test_inner_list_not_split():
    text = "1. Write code that does:\n  1. step\n  2. step\n2. Explain."
    assert len(split_questions(text)) == 2


def test_no_numbering():
    assert split_questions("Just one question") == ["Just one question"]

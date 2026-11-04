from assignment_solver.generate.prompt import SYSTEM_PROMPT, inference_messages, user_prompt


def test_prompt_requests_readable_and_complete_answers():
    assert "Answer every part" in SYSTEM_PROMPT
    assert "one long paragraph" in SYSTEM_PROMPT
    assert "Do not add a generic introduction" in SYSTEM_PROMPT
    assert "code block" in SYSTEM_PROMPT


def test_retrieved_answers_are_marked_as_style_only():
    prompt = user_prompt(
        "Explain SQL constraints.",
        examples=[{"instruction": "What is a key?", "output": {"blocks": []}}],
    )
    assert "style references only" in prompt
    assert "do not copy their facts" in prompt
    assert "Question:\nExplain SQL constraints." in prompt


def test_no_example_does_not_add_retrieval_caveat():
    messages = inference_messages("Explain SQL constraints.", [], 3500)
    assert "style references only" not in messages[1]["content"]

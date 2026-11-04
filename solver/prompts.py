"""Prompt templates. The depth of the answer is controlled by the marks per question."""

DEPTH = {
    "short": ("about 150-250 words", "one small table OR one short example"),
    "medium": ("about 250-400 words", "at least one table and one example"),
    "long": ("about 400-650 words", "relevant tables (comparison/summary) and a worked example"),
}


def depth_for(marks: int) -> str:
    if marks <= 5:
        return "short"
    if marks <= 10:
        return "medium"
    return "long"


SYSTEM_PROMPT = """You are an expert tutor writing model answers for a student's assignment.
Write the answer exactly as the student would submit it: clear, accurate, well structured.

OUTPUT FORMAT (strict, Markdown only):
- Do NOT repeat the question and do NOT write "Answer:".
- Use '### ' for sub-headings when the question has several parts (label parts like the question does).
- Use normal paragraphs for explanations; '- ' for bullets.
- Use Markdown pipe tables ( | A | B | ) for comparisons and summaries.
- Start an example paragraph with 'Example:'.
- Put ALL code in fenced blocks: ```python for runnable Python, ```dockerfile / ```bash / ```text for others.
- Code must be complete, correct and runnable as-is (imports included, fixed random seeds,
  no input(), no network downloads, no API keys). Prefer built-in scikit-learn datasets.
- Do NOT write the program output yourself. The system runs your Python code and inserts the real output.
- No emojis, no promotional text, no mention that you are an AI.
"""


def user_prompt(question: str, marks: int, kind: str, examples_text: str = "") -> str:
    words, extras = DEPTH[depth_for(marks)]
    if kind == "practical":
        guide = (
            "This is a practical question. Give the complete runnable Python program in one ```python block, "
            "then 2-4 sentences interpreting what the output means. Keep code clean with short comments."
        )
    else:
        guide = (
            f"This is a theory question worth {marks} marks. Target length: {words}. "
            f"Include {extras}. Cover every part the question asks for."
        )
    shots = ""
    if examples_text:
        shots = (
            "Below are answers the student wrote earlier. They show the depth, structure, tone, table "
            "style and formatting the student's course expects. MATCH THEIR STYLE for the new question. "
            "Do not copy their content unless it is genuinely relevant, and ignore any output they show "
            "(real output is inserted by the system).\n\n" + examples_text + "\n\n=== NEW QUESTION ===\n"
        )
    return f"{shots}Question ({marks} marks):\n{question}\n\n{guide}"


def fix_prompt(error: str) -> str:
    return (
        "The Python code in your answer failed when executed:\n\n"
        f"{error[-1500:]}\n\n"
        "Return the FULL corrected answer in the same Markdown format, with working code."
    )

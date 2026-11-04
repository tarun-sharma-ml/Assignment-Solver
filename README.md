# Assignment Solver

Turns an assignment PDF into a formatted Word document of answers using Google Gemini (default model `gemini-3.5-flash-lite`).

**Pipeline:** PDF -> parse questions -> Gemini writes each answer (tables, examples) ->
generated Python code is **executed** and the *real* output and plots are inserted ->
failing code is sent back to Gemini to fix -> `.docx` (Times New Roman 12 for text,
Courier New 10 for code and output).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then put your GEMINI_API_KEY in .env
```
If the assignment has practical questions, also install what the generated code may use, e.g.
`pip install numpy pandas matplotlib scikit-learn seaborn`.

## Usage
```bash
python main.py assignment.pdf --list                    # check the parsed questions first
python main.py assignment.pdf --marks 20 --name "Your Name"
python main.py assignment.pdf --only 1,3,6-8 --marks 10 --out answers.docx
python main.py assignment.pdf --no-run-code             # do not execute code
python main.py assignment.pdf --dry-run                 # test everything without an API key
```
| Option | Meaning |
|---|---|
| `--marks N` | Marks per question; controls answer depth (<=5 short, <=10 medium, else long). Auto-detected from "Each question carries N marks" |
| `--only 1,3,6-8` | Solve only some questions |
| `--model ID` | Gemini model id (or set `GEMINI_MODEL`) |
| `--max-fix N` | Auto-fix attempts for code that fails (default 2) |
| `--dry-run` | Mock model; checks parsing and Word export for free |

Answers are cached in `.cache/`, so re-running after an interruption does not re-bill finished questions.
Delete `.cache/` to regenerate. The document is saved after every question.

## Project layout
```
main.py                  CLI
solver/pdf_parser.py     question extraction (Question N:, 1., and auto-numbered lists)
solver/prompts.py        system/user prompts, depth by marks
solver/llm.py            Gemini client (+ mock)
solver/blocks.py         Markdown -> typed blocks
solver/code_runner.py    runs Python snippets, captures stdout and matplotlib figures
solver/pipeline.py       per-question solve / run / fix / cache loop
solver/docx_builder.py   Word export
```

## Security
`--run-code` (default) **executes model-generated Python on your computer**. A deny-list blocks
obvious dangers (`subprocess`, `os.system`, file deletion, network calls, `eval`), but it is not a
sandbox. For anything beyond your own homework, run the project inside Docker, or use `--no-run-code`.
Never commit `.env`.

## Limitations (read before submitting anything)
- Not executed or tested in this environment: the live Gemini call. Everything else (parsing, code
  execution, auto-fix loop, figures, Word export) was tested with the mock/scripted models.
- Code is only verified to *run*, not to be the best solution. Docker, FastAPI and other non-Python
  snippets are shown but not executed.
- PDF parsing is heuristic. Always run `--list` first; if the PDF is scanned (images) it needs OCR
  first, or pass a `.txt` file with numbered questions.
- Model answers can contain mistakes. Read, verify and understand them, and follow your
  institution's rules on AI assistance.

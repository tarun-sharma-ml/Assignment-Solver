"""Render solved questions into a Word document.
Theory text: Times New Roman 12.  Code and program output: Courier New 10."""
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

TEXT_FONT, CODE_FONT = "Times New Roman", "Courier New"
BLUE = RGBColor(0x1F, 0x4E, 0x79)
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|(?<!\*)\*[^*\s][^*]*\*(?!\*))")


def _font(run, name, size, bold=None, italic=None, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), name)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def _shade(el_pr, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    el_pr.append(shd)


def _spacing(p, before=0, after=6):
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)


def add_inline(p, text, size=12, bold=False, italic=False):
    """Handle **bold**, *italic* and `code` inside a paragraph."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            _font(p.add_run(part[2:-2]), TEXT_FONT, size, bold=True, italic=italic)
        elif part.startswith("`") and part.endswith("`"):
            _font(p.add_run(part[1:-1]), CODE_FONT, 10)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            _font(p.add_run(part[1:-1]), TEXT_FONT, size, bold=bold, italic=True)
        else:
            _font(p.add_run(part), TEXT_FONT, size, bold=bold, italic=italic)


class AnswerDocument:
    def __init__(self, title="Assignment Solutions", subtitle="", student=""):
        self.doc = Document()
        sec = self.doc.sections[0]
        sec.left_margin = sec.right_margin = Inches(1)
        sec.top_margin = sec.bottom_margin = Inches(1)
        normal = self.doc.styles["Normal"]
        normal.font.name = TEXT_FONT
        normal.font.size = Pt(12)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), TEXT_FONT)
        self._cover(title, subtitle, student)

    # ---------- structure ----------
    def _cover(self, title, subtitle, student):
        p = self.doc.add_paragraph()
        _font(p.add_run(title), TEXT_FONT, 20, bold=True)
        _spacing(p, 0, 4)
        if subtitle:
            p = self.doc.add_paragraph()
            _font(p.add_run(subtitle), TEXT_FONT, 12, bold=True)
            _spacing(p, 0, 4)
        if student:
            p = self.doc.add_paragraph()
            _font(p.add_run(f"Name: {student}"), TEXT_FONT, 12)
            _spacing(p, 0, 10)

    def add_question(self, number, text):
        p = self.doc.add_paragraph()
        _font(p.add_run(f"Question {number}: {text}"), TEXT_FONT, 13, bold=True, color=BLUE)
        p.paragraph_format.keep_with_next = True
        _spacing(p, 16, 4)
        p = self.doc.add_paragraph()
        _font(p.add_run("Answer:"), TEXT_FONT, 12, bold=True, italic=True)
        p.paragraph_format.keep_with_next = True
        _spacing(p, 2, 4)

    def add_blocks(self, blocks):
        for b in blocks:
            getattr(self, f"_render_{b.kind}", lambda _b: None)(b)

    # ---------- block renderers ----------
    def _render_heading(self, b):
        p = self.doc.add_paragraph()
        _font(p.add_run(b.text), TEXT_FONT, 12, bold=True)
        p.paragraph_format.keep_with_next = True
        _spacing(p, 8, 3)

    def _render_para(self, b):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if b.text.lower().startswith("example:"):
            _font(p.add_run("Example: "), TEXT_FONT, 12, bold=True, italic=True)
            add_inline(p, b.text[8:].strip(), italic=True)
        else:
            add_inline(p, b.text)
        _spacing(p, 0, 6)

    def _render_bullet(self, b):
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        _font(p.add_run("\u2022  "), TEXT_FONT, 12)
        add_inline(p, b.text)
        _spacing(p, 0, 3)

    def _render_number(self, b):
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        _font(p.add_run(f"{b.n}. "), TEXT_FONT, 12)
        add_inline(p, b.text)
        _spacing(p, 0, 3)

    def _render_table(self, b):
        rows = b.rows
        ncols = max(len(r) for r in rows)
        table = self.doc.add_table(rows=len(rows), cols=ncols)
        table.style = "Table Grid"
        for ri, row in enumerate(rows):
            for ci in range(ncols):
                cell = table.cell(ri, ci)
                cell.text = ""
                p = cell.paragraphs[0]
                _spacing(p, 1, 1)
                txt = row[ci] if ci < len(row) else ""
                if ri == 0:
                    _font(p.add_run(txt), TEXT_FONT, 11, bold=True, color=RGBColor(255, 255, 255))
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    _shade(cell._element.get_or_add_tcPr(), "1F4E79")
                else:
                    add_inline(p, txt, size=11, bold=(ci == 0))
                    if ci == 0:
                        _shade(cell._element.get_or_add_tcPr(), "EAF1F8")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def _label(self, text):
        p = self.doc.add_paragraph()
        _font(p.add_run(text), TEXT_FONT, 12, bold=True)
        p.paragraph_format.keep_with_next = True
        _spacing(p, 6, 2)

    def _code_lines(self, text):
        for line in (text.split("\n") or [""]):
            p = self.doc.add_paragraph()
            _font(p.add_run(line if line else " "), CODE_FONT, 10)
            _spacing(p, 0, 0)
            p.paragraph_format.left_indent = Inches(0.1)
            _shade(p._element.get_or_add_pPr(), "F2F2F2")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def _render_code(self, b):
        self._label("Code:")
        self._code_lines(b.text)

    def _render_output(self, b):
        self._label("Output:")
        self._code_lines(b.text)

    def _render_image(self, b):
        if Path(b.text).exists():
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(b.text, width=Inches(4.6))
            _spacing(p, 2, 8)

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(path)

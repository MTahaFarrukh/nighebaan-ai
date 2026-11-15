"""Build the Nigehbaan AI CCP report DOCX from the maintained Markdown report."""

from __future__ import annotations

import re
from pathlib import Path

import cairosvg
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "report" / "Nigehbaan_AI_CCP_Report.md"
OUTPUT = ROOT / "report" / "Nigehbaan_AI_CCP_Report.docx"
FIGURES = ROOT / "report" / "figures"
TMP = ROOT / "tmp" / "report-docx"


def set_cell_shading(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_border(cell, color: str = "D9E2F3") -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = properties.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), color)


def set_cell_text(cell, text: str, *, header: bool = False) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(clean_inline(text))
    run.font.name = "Aptos"
    run.font.size = Pt(9)
    if header:
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def clean_inline(text: str) -> str:
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("`", "")
    return text.strip()


def add_paragraph(doc: Document, text: str, *, quote: bool = False) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.line_spacing = 1.08
    if quote:
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.right_indent = Inches(0.2)
    run = paragraph.add_run(clean_inline(text))
    run.font.name = "Aptos"
    run.font.size = Pt(10.5)
    if quote:
        run.italic = True
        run.font.color.rgb = RGBColor(80, 80, 80)


def add_table(doc: Document, rows: list[str]) -> None:
    parsed = [[part.strip() for part in row.strip().strip("|").split("|")] for row in rows]
    parsed = [row for row in parsed if row and not all(re.fullmatch(r":?-{3,}:?", part) for part in row)]
    if not parsed:
        return
    table = doc.add_table(rows=len(parsed), cols=max(len(row) for row in parsed))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for row_index, row in enumerate(parsed):
        for col_index, value in enumerate(row):
            cell = table.cell(row_index, col_index)
            set_cell_shading(cell, "1F4E79" if row_index == 0 else ("F4F7FB" if row_index % 2 == 0 else "FFFFFF"))
            set_cell_border(cell)
            set_cell_text(cell, value, header=row_index == 0)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_footer(section) -> None:
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.text = "Nigehbaan AI | CT-361 AI and Expert Systems"
    footer.runs[0].font.name = "Aptos"
    footer.runs[0].font.size = Pt(8)
    footer.runs[0].font.color.rgb = RGBColor(100, 100, 100)


def add_figures(doc: Document) -> None:
    figure_order = [
        ("fig1_architecture.svg", "Figure 1. System architecture and main data flow."),
        ("fig2_text_val_macro_f1.svg", "Figure 2. Text model validation macro-F1 comparison."),
        ("fig3_hybrid_val_macro_f1.svg", "Figure 3. Hybrid validation macro-F1 comparison."),
        ("fig4_ablation_val_macro_f1.svg", "Figure 4. Validation ablation study."),
        ("fig5_text_test_ml_confusion.svg", "Figure 5. Text ML test confusion matrix."),
        ("fig6_text_test_hybrid_confusion.svg", "Figure 6. Hybrid test confusion matrix."),
        ("fig7_url_test_confusion.svg", "Figure 7. URL test confusion matrix."),
        ("fig8_train_class_counts.svg", "Figure 8. Training class distribution."),
    ]
    doc.add_page_break()
    doc.add_heading("Appendix C — Evaluation Figures", level=1)
    add_paragraph(doc, "The following figures are generated from the frozen evaluation artifacts and are included to make the results reproducible and easy to inspect.")
    TMP.mkdir(parents=True, exist_ok=True)
    for svg_name, caption in figure_order:
        svg = FIGURES / svg_name
        if not svg.exists():
            continue
        png = TMP / (svg.stem + ".png")
        cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1500)
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(str(png), width=Inches(6.1))
        caption_paragraph = doc.add_paragraph(caption)
        caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption_paragraph.runs[0].italic = True
        caption_paragraph.runs[0].font.size = Pt(9)


def build() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    add_footer(section)

    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)
    for name, size, color in (("Heading 1", 16, "1F4E79"), ("Heading 2", 13, "2F75B5"), ("Heading 3", 11, "2F75B5")):
        style = styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(45)
    title.paragraph_format.space_after = Pt(8)
    run = title.add_run("Nigehbaan AI")
    run.bold = True
    run.font.name = "Aptos Display"
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(31, 78, 121)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(25)
    run = subtitle.add_run("Multimodal Roman Urdu Scam and Abuse Detection\nwith a Hybrid Expert System")
    run.font.name = "Aptos"
    run.font.size = Pt(15)
    run.font.color.rgb = RGBColor(70, 70, 70)
    details = doc.add_paragraph()
    details.alignment = WD_ALIGN_PARAGRAPH.CENTER
    details.add_run("CT-361 — AI and Expert Systems\nCourse Project Report\nNovember 2026").font.size = Pt(11)
    doc.add_page_break()

    doc.add_heading("Contents", level=1)
    major_headings = [clean_inline(line[3:]) for line in lines if line.startswith("## ")]
    for index, heading in enumerate(major_headings, start=1):
        paragraph = doc.add_paragraph(style="List Number")
        paragraph.paragraph_format.left_indent = Inches(0.2)
        paragraph.add_run(heading)
    doc.add_page_break()

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.startswith("---"):
            index += 1
            continue
        if line.startswith("# "):
            index += 1
            continue
        if line.startswith("## "):
            doc.add_heading(clean_inline(line[3:]), level=1)
            index += 1
            continue
        if line.startswith("### "):
            doc.add_heading(clean_inline(line[4:]), level=2)
            index += 1
            continue
        if line.startswith("#### "):
            doc.add_heading(clean_inline(line[5:]), level=3)
            index += 1
            continue
        if line.startswith("```"):
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.25)
            paragraph.paragraph_format.space_after = Pt(5)
            run = paragraph.add_run("\n".join(code_lines))
            run.font.name = "Consolas"
            run.font.size = Pt(8.5)
            continue
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            add_table(doc, table_lines)
            continue
        if line.startswith("> "):
            add_paragraph(doc, line[2:], quote=True)
            index += 1
            continue
        if line.startswith("- ") or re.match(r"\d+\. ", line):
            paragraph = doc.add_paragraph(style="List Bullet" if line.startswith("- ") else "List Number")
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.add_run(clean_inline(re.sub(r"^(?:- |\d+\. )", "", line)))
            index += 1
            continue
        add_paragraph(doc, line)
        index += 1

    add_figures(doc)
    doc.core_properties.title = "Nigehbaan AI CCP Report"
    doc.core_properties.subject = "CT-361 AI and Expert Systems course project"
    doc.core_properties.author = "Nigehbaan AI Project Team"
    doc.core_properties.keywords = "Roman Urdu, scam detection, expert system, machine learning"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()

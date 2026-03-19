# raftsecretary/export/pdf_builder.py
from __future__ import annotations
from pathlib import Path
from fpdf import FPDF

FONTS_DIR = Path(__file__).parent / "fonts"
FONT_REGULAR = str(FONTS_DIR / "DejaVuSans.ttf")
FONT_BOLD = str(FONTS_DIR / "DejaVuSans-Bold.ttf")

PAGE_W = 297   # A4 landscape mm
PAGE_H = 210
MARGIN = 12
CONTENT_W = PAGE_W - 2 * MARGIN


def new_pdf() -> FPDF:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_font("DejaVu", "", FONT_REGULAR, uni=True)
    pdf.add_font("DejaVu", "B", FONT_BOLD, uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    return pdf


def write_doc_header(
    pdf: FPDF,
    discipline_label: str,
    comp_name: str,
    comp_dates: str,
    venue: str,
    organizer: str,
) -> None:
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(CONTENT_W, 7, "ИТОГОВЫЙ ПРОТОКОЛ", align="C", ln=True)
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(CONTENT_W, 6, f"Дисциплина: {discipline_label}", align="C", ln=True)
    pdf.ln(2)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(CONTENT_W / 2, 5, f"Соревнование: {comp_name}", ln=False)
    pdf.cell(CONTENT_W / 2, 5, f"Организатор: {organizer}", ln=True)
    pdf.cell(CONTENT_W / 2, 5, f"Даты: {comp_dates}", ln=False)
    pdf.cell(CONTENT_W / 2, 5, f"Место проведения: {venue}", ln=True)
    pdf.ln(3)


def write_category_header(pdf: FPDF, label: str) -> None:
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(CONTENT_W, 6, label, ln=True)
    pdf.ln(1)


def write_table_header(pdf: FPDF, cols: list[tuple[str, float]]) -> None:
    """cols: list of (label, width_mm)"""
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    for label, w in cols:
        pdf.cell(w, 6, label, border=1, align="C", fill=True)
    pdf.ln()


def write_table_row(pdf: FPDF, cells: list[tuple[str, float]], align: str = "L") -> None:
    pdf.set_font("DejaVu", "", 8)
    for text, w in cells:
        pdf.cell(w, 5, text, border=1, align=align)
    pdf.ln()


def write_footer(pdf: FPDF, chief_judge: str, chief_secretary: str) -> None:
    pdf.ln(5)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(CONTENT_W / 2, 5, f"Главный судья: {chief_judge}", ln=False)
    pdf.cell(CONTENT_W / 2, 5, f"Главный секретарь: {chief_secretary}", ln=True)


def pdf_bytes(pdf: FPDF) -> bytes:
    return pdf.output()

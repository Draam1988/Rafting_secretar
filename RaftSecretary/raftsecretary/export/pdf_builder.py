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


def write_table_row_multiline(
    pdf: FPDF,
    cells_before: list[tuple[str, float]],
    multiline_text: str,
    multiline_width: float,
    cells_after: list[tuple[str, float]],
    line_h: float = 4.5,
) -> None:
    """Draw a table row where one column contains multi-line text (\\n-separated).

    All other cells are drawn with a fixed height equal to line_h * number_of_lines
    so the row stays aligned. The multiline column uses multi_cell().
    """
    x0 = pdf.get_x()
    y0 = pdf.get_y()

    lines = multiline_text.split("\n") if multiline_text else [""]
    n_lines = max(1, len(lines))
    row_h = line_h * n_lines

    pdf.set_font("DejaVu", "", 8)

    # Draw cells to the left of the multiline column
    for text, w in cells_before:
        pdf.cell(w, row_h, text, border=1)
    ml_x = pdf.get_x()

    # Skip over multiline column, draw cells to the right
    pdf.set_x(ml_x + multiline_width)
    for text, w in cells_after:
        pdf.cell(w, row_h, text, border=1)
    pdf.ln()

    # Now fill the multiline column at saved position
    pdf.set_xy(ml_x, y0)
    pdf.multi_cell(multiline_width, line_h, multiline_text, border=1)

    # Move cursor to start of next row
    pdf.set_xy(x0, y0 + row_h)


def write_footer(pdf: FPDF, chief_judge: str, chief_secretary: str) -> None:
    pdf.ln(5)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(CONTENT_W / 2, 5, f"Главный судья: {chief_judge}", ln=False)
    pdf.cell(CONTENT_W / 2, 5, f"Главный секретарь: {chief_secretary}", ln=True)


def pdf_bytes(pdf: FPDF) -> bytes:
    return bytes(pdf.output())

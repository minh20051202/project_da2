#!/usr/bin/env python3
"""Build the three Week-2 deliverables for project_da2.

Outputs are generated under resources/docs.  The script intentionally keeps the
architecture and evaluation plan implementation-neutral so they remain valid
while the project selects concrete models and vector stores in later weeks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Nop_Bao_Cao_Tung_Tuan" / "Tuan_02"

REPORT_PATH = OUT / "DA2_NguyenTuanMinh_Tuan2_BaoCaoTongQuanLyThuyet_YeuCauNghiepVu.docx"
ARCH_SVG = OUT / "DA2_NguyenTuanMinh_Tuan2_SoDoKienTrucTongThe_QuyTrinh.svg"
ARCH_PNG = OUT / "DA2_NguyenTuanMinh_Tuan2_SoDoKienTrucTongThe_QuyTrinh.png"
# The simplified V2 is now the official diagram written to the final filenames.
ARCH_V2_SVG = ARCH_SVG
ARCH_V2_PNG = ARCH_PNG
SPEC_PATH = OUT / "DA2_NguyenTuanMinh_Tuan2_DacTaPhamVi_DoiChung_DanhGia.docx"

NAVY = "16324F"
BLUE = "2166AC"
TEAL = "168AAD"
GREEN = "2A9D8F"
ORANGE = "E07A2D"
RED = "B33A3A"
LIGHT_BLUE = "EAF2F8"
LIGHT_GREEN = "EAF6F2"
LIGHT_ORANGE = "FFF3E8"
LIGHT_GREY = "F2F4F6"
MID_GREY = "D8DEE4"
WHITE = "FFFFFF"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=90, bottom=80, end=90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    keep = OxmlElement("w:keepNext")
    p_pr.append(keep)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Trang ")
    run.font.size = Pt(9)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])


def add_hyperlink(paragraph, text: str, url: str, color=BLUE, underline=True):
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    r_pr.append(c)
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        r_pr.append(u)
    run.append(r_pr)
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return hyperlink


def setup_document(title: str, subtitle: str) -> Document:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.0)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color in (
        ("Title", 20, NAVY),
        ("Subtitle", 13, BLUE),
        ("Heading 1", 15, NAVY),
        ("Heading 2", 13, BLUE),
        ("Heading 3", 12, TEAL),
    ):
        style = styles[name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)

    if "Caption VN" not in styles:
        cap = styles.add_style("Caption VN", WD_STYLE_TYPE.PARAGRAPH)
        cap.font.name = "Times New Roman"
        cap._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        cap.font.size = Pt(10)
        cap.font.italic = True
        cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(8)

    header = section.header.paragraphs[0]
    header.text = "ĐỒ ÁN 2 – NGUYỄN TUẤN MINH – TUẦN 02"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.name = "Arial"
    header.runs[0].font.size = Pt(8)
    header.runs[0].font.color.rgb = RGBColor.from_string("6B7785")
    add_page_number(section.footer.paragraphs[0])

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ĐẠI HỌC BÁCH KHOA HÀ NỘI")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor.from_string(NAVY)

    doc.add_paragraph("ĐỒ ÁN 2 – MI3390", style="Subtitle").alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(title, style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(28)
    p.paragraph_format.space_after = Pt(14)
    p = doc.add_paragraph(subtitle)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].italic = True
    p.runs[0].font.size = Pt(13)

    info = doc.add_table(rows=5, cols=2)
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    info.style = "Table Grid"
    rows = [
        ("Sinh viên", "Nguyễn Tuấn Minh"),
        ("MSSV", "20237465"),
        ("Giảng viên hướng dẫn", "PGS.TS. Trần Ngọc Thăng"),
        ("Thời điểm báo cáo", "Tuần 02 – ngày 01/10/2026"),
        ("Đề tài", "Agentic RAG hỗ trợ kiểm tra và hoàn thiện giải trình thuế GTGT đối với hoạt động xuất khẩu, tích hợp Lean 4"),
    ]
    for i, (k, v) in enumerate(rows):
        info.cell(i, 0).text = k
        info.cell(i, 1).text = v
        set_cell_shading(info.cell(i, 0), LIGHT_BLUE)
        for c in info.rows[i].cells:
            set_cell_margins(c)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        info.cell(i, 0).paragraphs[0].runs[0].bold = True
    doc.add_paragraph()
    p = doc.add_paragraph("Hà Nội, 01/10/2026")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].italic = True
    doc.add_page_break()
    return doc


def add_toc_placeholder(doc: Document) -> None:
    doc.add_heading("MỤC LỤC", level=1)
    p = doc.add_paragraph()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    hint = OxmlElement("w:t")
    hint.text = "Mở tài liệu trong Word và chọn Update Field để cập nhật mục lục."
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run = p.add_run()
    run._r.extend([fld_begin, instr, fld_sep, hint, fld_end])
    doc.add_page_break()


def add_bullets(doc: Document, items: Iterable[str], level=0) -> None:
    style = "List Bullet" if level == 0 else "List Bullet 2"
    for item in items:
        p = doc.add_paragraph(item, style=style)
        p.paragraph_format.left_indent = Cm(0.7 + 0.5 * level)
        p.paragraph_format.first_line_indent = Cm(-0.25)


def add_numbered(doc: Document, items: Iterable[str]) -> None:
    for item in items:
        p = doc.add_paragraph(item, style="List Number")
        p.paragraph_format.left_indent = Cm(0.7)
        p.paragraph_format.first_line_indent = Cm(-0.25)


def add_note(doc: Document, title: str, text: str, color=LIGHT_ORANGE) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_shading(cell, color)
    set_cell_margins(cell, 120, 140, 120, 140)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(title + ": ")
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(NAVY)
    p.add_run(text)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_table(doc: Document, headers: Sequence[str], rows: Sequence[Sequence[str]], widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, h in enumerate(headers):
        hdr.cells[i].text = h
        set_cell_shading(hdr.cells[i], NAVY)
        hdr.cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for run in hdr.cells[i].paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = RGBColor.from_string(WHITE)
            run.font.name = "Arial"
            run.font.size = Pt(9)
        set_cell_margins(hdr.cells[i])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            if ridx % 2 == 1:
                set_cell_shading(cells[i], "F8FAFC")
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(2)
                for run in p.runs:
                    run.font.size = Pt(9)
            set_cell_margins(cells[i])
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def box(ax, xy, wh, text, fc, ec=NAVY, fontsize=9, lw=1.2, radius=0.02):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        linewidth=lw, edgecolor=f"#{ec}", facecolor=f"#{fc}",
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color=f"#{NAVY}", wrap=True, fontweight="semibold")
    return patch


def arrow(ax, a, b, color=NAVY, rad=0.0, lw=1.2, style="-|>"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=12,
                                 linewidth=lw, color=f"#{color}",
                                 connectionstyle=f"arc3,rad={rad}"))


def build_architecture_figure() -> None:
    fig = plt.figure(figsize=(16, 15), dpi=180, facecolor="white")
    gs = fig.add_gridspec(3, 1, height_ratios=[1.38, 0.95, 1.0], hspace=0.13)

    # Panel A: architecture
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.01, 0.97, "A. KIẾN TRÚC TỔNG THỂ", fontsize=15, fontweight="bold", color=f"#{NAVY}", va="top")

    ax.add_patch(FancyBboxPatch((0.015, 0.58), 0.97, 0.34, boxstyle="round,pad=0.008",
                                fc="#F5F8FB", ec="#B8C6D1", lw=1.0))
    ax.text(0.028, 0.895, "LUỒNG NGOẠI TUYẾN: QUẢN TRỊ TRI THỨC PHÁP LUẬT", fontsize=10,
            color=f"#{BLUE}", fontweight="bold")
    offline = [
        (0.04, "Nguồn pháp luật\nchính thức", LIGHT_BLUE),
        (0.20, "Chuẩn hóa + metadata\nhiệu lực/phiên bản", LIGHT_BLUE),
        (0.36, "Chia đoạn + chỉ mục\ntừ khóa/ngữ nghĩa", LIGHT_BLUE),
        (0.55, "Rà soát ngữ nghĩa\nquy tắc ứng viên", LIGHT_ORANGE),
        (0.73, "Kho quy tắc Lean\nđã duyệt, có phiên bản", LIGHT_GREEN),
    ]
    for x, text_, fc in offline:
        box(ax, (x, 0.68), (0.13 if x != 0.73 else 0.20, 0.13), text_, fc, fontsize=8.5)
    for x1, x2 in [(0.17, 0.20), (0.33, 0.36), (0.49, 0.55), (0.68, 0.73)]:
        arrow(ax, (x1, 0.745), (x2, 0.745), BLUE)
    box(ax, (0.36, 0.59), (0.13, 0.06), "Kho trích dẫn", "FFFFFF", BLUE, fontsize=8)
    arrow(ax, (0.425, 0.68), (0.425, 0.65), BLUE)

    ax.add_patch(FancyBboxPatch((0.015, 0.17), 0.97, 0.36, boxstyle="round,pad=0.008",
                                fc="#FBFCFD", ec="#B8C6D1", lw=1.0))
    ax.text(0.028, 0.50, "LUỒNG TRỰC TUYẾN: XỬ LÝ MỘT HỒ SƠ / CÂU HỎI", fontsize=10,
            color=f"#{TEAL}", fontweight="bold")
    online = [
        (0.03, 0.30, 0.105, "Câu hỏi +\nhồ sơ"),
        (0.16, 0.30, 0.12, "Nạp, OCR,\nẩn danh"),
        (0.305, 0.30, 0.13, "Đồ thị hồ sơ +\nkho bằng chứng"),
        (0.46, 0.30, 0.13, "Bộ điều phối\ncó giới hạn"),
        (0.62, 0.30, 0.13, "Gói căn cứ +\nnghĩa vụ chứng minh"),
        (0.78, 0.30, 0.09, "Lean 4 RUNTIME\nkiểm chứng"),
        (0.895, 0.30, 0.08, "Cổng\nđầu ra"),
    ]
    for x, y, w, text_ in online:
        fc = LIGHT_GREEN if "Lean" in text_ else (LIGHT_ORANGE if "điều phối" in text_ else LIGHT_BLUE)
        box(ax, (x, y), (w, 0.12), text_, fc, fontsize=8.2)
    for x1, x2 in [(0.135, 0.16), (0.28, 0.305), (0.435, 0.46), (0.59, 0.62), (0.75, 0.78), (0.87, 0.895)]:
        arrow(ax, (x1, 0.36), (x2, 0.36), TEAL)
    box(ax, (0.46, 0.19), (0.13, 0.07), "RAG + công cụ\nđối chiếu", "FFFFFF", TEAL, fontsize=8)
    arrow(ax, (0.525, 0.30), (0.525, 0.26), TEAL)
    arrow(ax, (0.49, 0.59), (0.525, 0.42), BLUE, rad=-0.05)
    arrow(ax, (0.83, 0.68), (0.825, 0.42), GREEN, rad=0.02)
    arrow(ax, (0.825, 0.425), (0.55, 0.425), ORANGE, rad=0.28, lw=1.5)
    ax.text(0.665, 0.475, "proof state / compiler feedback / goal còn mở",
            fontsize=7.2, color=f"#{ORANGE}", ha="center", fontweight="bold")
    box(ax, (0.72, 0.19), (0.14, 0.07), "Sinh giải trình\nbám nguồn", "FFFFFF", TEAL, fontsize=8)
    arrow(ax, (0.75, 0.30), (0.79, 0.26), TEAL, rad=0.1)
    arrow(ax, (0.86, 0.225), (0.925, 0.30), TEAL, rad=-0.1)

    box(ax, (0.81, 0.055), (0.165, 0.075), "Kết quả: đạt / chưa đủ\n/ mâu thuẫn / chuyển người", LIGHT_ORANGE, ORANGE, fontsize=8)
    arrow(ax, (0.935, 0.30), (0.91, 0.13), ORANGE, rad=0.08)
    box(ax, (0.46, 0.055), (0.25, 0.075), "Nhật ký truy vết: nguồn, phiên bản, bước,\ncông cụ, bằng chứng, proof ID, chi phí", LIGHT_GREY, NAVY, fontsize=8)
    arrow(ax, (0.525, 0.19), (0.585, 0.13), NAVY, rad=0.08)
    arrow(ax, (0.895, 0.34), (0.71, 0.095), NAVY, rad=0.12)

    ax.text(0.025, 0.012,
            "Nguyên tắc: Lean PASS chỉ xác nhận kết luận suy ra từ quy tắc và giả thiết đã mã hóa; không xác nhận tính thật của chứng từ hoặc tính đầy đủ của truy xuất.",
            fontsize=8.3, color=f"#{RED}", fontweight="bold")

    # Panel B: expanded runtime reasoning loop
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")
    ax2.text(0.01, 0.97, "B. LEAN 4 LÀ RUNTIME TRONG VÒNG SUY LUẬN CỦA AGENT", fontsize=15,
             fontweight="bold", color=f"#{NAVY}", va="top")
    ax2.add_patch(FancyBboxPatch((0.015, 0.08), 0.97, 0.78, boxstyle="round,pad=0.010",
                                 fc="#FBFCFD", ec="#B8C6D1", lw=1.0))

    box(ax2, (0.035, 0.47), (0.115, 0.18), "Trạng thái ca\n+ mục tiêu\n+ ngân sách", LIGHT_BLUE, BLUE, fontsize=8.5)
    box(ax2, (0.19, 0.47), (0.15, 0.18), "AGENT / ORCHESTRATOR\nlập kế hoạch +\nchọn hành động", LIGHT_ORANGE, ORANGE, fontsize=9)
    box(ax2, (0.19, 0.17), (0.15, 0.16), "RAG + công cụ hồ sơ\ntruy xuất / đối chiếu /\nphát hiện thiếu", "FFFFFF", TEAL, fontsize=8)
    box(ax2, (0.39, 0.47), (0.14, 0.18), "Proof-obligation\nbuilder\n(rule + facts + goal)", LIGHT_BLUE, BLUE, fontsize=8.5)
    box(ax2, (0.58, 0.38), (0.18, 0.36),
        "LEAN 4 RUNTIME\n\n1. Nạp rule version\n2. Elaborate/typecheck\n3. Chạy tactic/proof\n4. Kernel kiểm tra\n5. Kiểm tra sorry/admit/axiom",
        LIGHT_GREEN, GREEN, fontsize=8.3, lw=2.0)
    box(ax2, (0.81, 0.56), (0.15, 0.16), "PASS hợp lệ\n+ proof artifact ID", LIGHT_GREEN, GREEN, fontsize=8.5)
    box(ax2, (0.81, 0.25), (0.15, 0.18), "FAIL / OPEN GOALS\ncompiler feedback\n+ proof state", LIGHT_ORANGE, ORANGE, fontsize=8.5)
    box(ax2, (0.81, 0.08), (0.15, 0.10), "Hết ngân sách:\nchưa đủ / chuyển người", "FFF3E8", RED, fontsize=8)

    arrow(ax2, (0.15, 0.56), (0.19, 0.56), TEAL, lw=1.5)
    arrow(ax2, (0.265, 0.47), (0.265, 0.33), TEAL, lw=1.5)
    arrow(ax2, (0.34, 0.25), (0.39, 0.50), TEAL, rad=-0.08, lw=1.5)
    arrow(ax2, (0.34, 0.56), (0.39, 0.56), TEAL, lw=1.5)
    arrow(ax2, (0.53, 0.56), (0.58, 0.56), GREEN, lw=1.7)
    ax2.text(0.552, 0.60, "gọi runtime", fontsize=7.5, color=f"#{GREEN}", ha="center", fontweight="bold")
    arrow(ax2, (0.76, 0.62), (0.81, 0.64), GREEN, lw=1.7)
    arrow(ax2, (0.76, 0.45), (0.81, 0.34), ORANGE, lw=1.7)
    arrow(ax2, (0.81, 0.34), (0.34, 0.58), ORANGE, rad=0.30, lw=1.8)
    ax2.text(0.56, 0.82, "PHẢN HỒI TRONG LÚC SUY LUẬN: sửa tactic / truy xuất thêm / đổi nhánh / dừng",
             fontsize=8.4, color=f"#{ORANGE}", ha="center", fontweight="bold")
    arrow(ax2, (0.885, 0.25), (0.885, 0.18), RED, lw=1.4)
    ax2.text(0.02, 0.015,
             "Lean 4 không chỉ là bộ kiểm tra cuối: Agent gọi Lean nhiều lần trong giới hạn để nhận proof state và compiler feedback. Tuy nhiên Agent không được thay theorem hoặc rule version đã duyệt.",
             fontsize=8.3, color=f"#{RED}", fontweight="bold")

    # Panel C: end-to-end process
    ax3 = fig.add_subplot(gs[2])
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis("off")
    ax3.text(0.01, 0.97, "C. QUY TRÌNH XỬ LÝ DỰ KIẾN", fontsize=15, fontweight="bold", color=f"#{NAVY}", va="top")
    labels = [
        "1. Chốt thời điểm\n& phiên bản luật",
        "2. Tiếp nhận, OCR\n& chuẩn hóa hồ sơ",
        "3. Truy xuất căn cứ\n& kiểm tra trích dẫn",
        "4. Lập chuỗi\nbằng chứng",
        "5. Phát hiện thiếu\nhoặc mâu thuẫn",
        "6. Chọn nhánh\nkiểm chứng",
        "7. Sinh giải trình\n& cổng đầu ra",
        "8. Trả kết quả\n& lưu truy vết",
    ]
    xs = [0.025, 0.15, 0.275, 0.40, 0.525, 0.65, 0.775, 0.895]
    widths = [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.085]
    for i, (x, w, label) in enumerate(zip(xs, widths, labels)):
        fc = LIGHT_ORANGE if i in (4, 5, 7) else LIGHT_BLUE
        box(ax3, (x, 0.58), (w, 0.18), label, fc, fontsize=7.8)
        if i < len(labels) - 1:
            arrow(ax3, (x + w, 0.67), (xs[i + 1], 0.67), TEAL)

    box(ax3, (0.58, 0.19), (0.16, 0.16), "Đủ điều kiện\nhình thức hóa?", LIGHT_ORANGE, ORANGE, fontsize=9)
    arrow(ax3, (0.70, 0.58), (0.67, 0.35), ORANGE, rad=0.05)
    box(ax3, (0.36, 0.08), (0.16, 0.12), "KHÔNG: trả lời bám nguồn\n+ nêu giới hạn", LIGHT_BLUE, BLUE, fontsize=8)
    box(ax3, (0.78, 0.08), (0.16, 0.12), "CÓ: chạy vòng Agent ↔ Lean\ntrong giới hạn", LIGHT_GREEN, GREEN, fontsize=8)
    arrow(ax3, (0.58, 0.26), (0.52, 0.14), BLUE)
    arrow(ax3, (0.74, 0.26), (0.78, 0.14), GREEN)
    ax3.text(0.48, 0.235, "Không", fontsize=8, color=f"#{BLUE}")
    ax3.text(0.765, 0.235, "Có", fontsize=8, color=f"#{GREEN}")
    arrow(ax3, (0.52, 0.14), (0.82, 0.58), NAVY, rad=-0.18)
    arrow(ax3, (0.94, 0.14), (0.84, 0.58), NAVY, rad=0.18)
    ax3.text(0.02, 0.015,
             "Nếu thiếu/xung đột bằng chứng hoặc Lean không chứng minh được: không tự động kết luận bất lợi; hệ thống yêu cầu bổ sung, nêu mâu thuẫn hoặc chuyển người rà soát.",
             fontsize=8.3, color=f"#{RED}", fontweight="bold")

    fig.suptitle(
        "Hệ thống Agentic RAG + Lean 4 cho kiểm tra và hoàn thiện giải trình thuế GTGT đối với hoạt động xuất khẩu",
        fontsize=17, color=f"#{NAVY}", fontweight="bold", y=0.995,
    )
    fig.savefig(ARCH_PNG, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(ARCH_SVG, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_architecture_v2_figure() -> None:
    """A cleaner comparison draft: overview + explicit Agent/Lean runtime loop."""
    fig = plt.figure(figsize=(16, 10.5), dpi=180, facecolor="white")
    gs = fig.add_gridspec(2, 1, height_ratios=[0.86, 1.14], hspace=0.16)

    # A. Minimal system architecture
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.95, "A. CÁC THÀNH PHẦN CHÍNH", fontsize=16,
            fontweight="bold", color=f"#{NAVY}", va="top")

    ax.text(0.03, 0.80, "DỮ LIỆU ĐƯỢC CHUẨN BỊ TRƯỚC", fontsize=9.5,
            color=f"#{BLUE}", fontweight="bold")
    box(ax, (0.04, 0.60), (0.16, 0.14), "Nguồn pháp luật\nchính thức", LIGHT_BLUE, BLUE, fontsize=9)
    box(ax, (0.25, 0.60), (0.20, 0.14), "Kho văn bản pháp luật\n+ công cụ tìm kiếm", LIGHT_BLUE, BLUE, fontsize=9)
    box(ax, (0.50, 0.60), (0.19, 0.14), "Các quy tắc Lean\nđã được kiểm tra", LIGHT_GREEN, GREEN, fontsize=9)
    arrow(ax, (0.20, 0.67), (0.25, 0.67), BLUE, lw=1.6)
    arrow(ax, (0.45, 0.67), (0.50, 0.67), BLUE, lw=1.6)

    ax.text(0.03, 0.45, "KHI NGƯỜI DÙNG GỬI HỒ SƠ", fontsize=9.5,
            color=f"#{TEAL}", fontweight="bold")
    box(ax, (0.04, 0.20), (0.13, 0.16), "Câu hỏi\n+ hồ sơ", "FFFFFF", TEAL, fontsize=9)
    box(ax, (0.21, 0.20), (0.15, 0.16), "Đọc và sắp xếp\nthông tin trong hồ sơ", LIGHT_BLUE, TEAL, fontsize=9)
    box(ax, (0.41, 0.16), (0.24, 0.24),
        "AGENT XỬ LÝ THEO SỐ BƯỚC GIỚI HẠN\n\nLên kế hoạch • tìm quy định\nkiểm tra hồ sơ • gọi Lean 4\nnhận kết quả • quyết định dừng",
        LIGHT_ORANGE, ORANGE, fontsize=9.2, lw=2.0)
    box(ax, (0.69, 0.20), (0.12, 0.16), "Bước kiểm tra\ncuối cùng", LIGHT_GREY, NAVY, fontsize=9)
    box(ax, (0.84, 0.16), (0.15, 0.24),
        "KẾT QUẢ\n\n• Trả lời kèm nguồn\n• Cần thêm hồ sơ\n• Cần người kiểm tra",
        "FFFFFF", NAVY, fontsize=8.6)
    for a, b in [((0.17, 0.28), (0.21, 0.28)), ((0.36, 0.28), (0.41, 0.28)),
                 ((0.65, 0.28), (0.69, 0.28)), ((0.81, 0.28), (0.84, 0.28))]:
        arrow(ax, a, b, TEAL, lw=1.7)
    arrow(ax, (0.35, 0.60), (0.48, 0.40), BLUE, rad=-0.08, lw=1.5)
    arrow(ax, (0.595, 0.60), (0.58, 0.40), GREEN, rad=0.04, lw=1.5)
    ax.text(0.38, 0.49, "quy định và nguồn", fontsize=7.6, color=f"#{BLUE}", ha="center")
    ax.text(0.62, 0.49, "quy tắc đã kiểm tra", fontsize=7.6, color=f"#{GREEN}", ha="center")
    ax.text(0.03, 0.055,
            "Agent chỉ được dùng văn bản và quy tắc đã kiểm tra; Agent không được tự sửa nội dung pháp luật.",
            fontsize=8.5, color=f"#{RED}", fontweight="bold")

    # B. Explicit bounded Agent <-> Lean runtime loop
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")
    ax2.text(0.02, 0.96, "B. AGENT GỌI LEAN 4 TRONG QUÁ TRÌNH XỬ LÝ", fontsize=16,
             fontweight="bold", color=f"#{NAVY}", va="top")
    ax2.add_patch(FancyBboxPatch((0.02, 0.09), 0.96, 0.76, boxstyle="round,pad=0.010",
                                 fc="#FBFCFD", ec="#B8C6D1", lw=1.1))

    box(ax2, (0.04, 0.48), (0.14, 0.16), "1. AGENT\nxem thông tin đang có\nvà lên kế hoạch", LIGHT_ORANGE, ORANGE, fontsize=9)
    box(ax2, (0.23, 0.48), (0.15, 0.16), "2. Chọn quy định,\nchứng từ và\nquy tắc Lean", LIGHT_BLUE, BLUE, fontsize=9)
    box(ax2, (0.43, 0.48), (0.14, 0.16), "3. Tạo bài toán\ncần Lean 4\nkiểm tra", LIGHT_BLUE, BLUE, fontsize=8.9)
    box(ax2, (0.62, 0.43), (0.16, 0.26),
        "4. LEAN 4 KIỂM TRA\n\nNạp quy tắc và dữ kiện\nChạy phần chứng minh\nLean xác nhận kết quả\nKhông còn phần bỏ trống",
        LIGHT_GREEN, GREEN, fontsize=8.6, lw=2.0)
    box(ax2, (0.83, 0.57), (0.13, 0.14), "LEAN KIỂM TRA\nTHÀNH CÔNG\n→ lưu mã kết quả", LIGHT_GREEN, GREEN, fontsize=8.4)
    box(ax2, (0.83, 0.37), (0.13, 0.14), "LEAN CHƯA\nKIỂM TRA XONG\n→ trả lỗi và phần còn thiếu", LIGHT_ORANGE, ORANGE, fontsize=8.2)

    for a, b, c in [((0.18, 0.56), (0.23, 0.56), TEAL),
                    ((0.38, 0.56), (0.43, 0.56), TEAL),
                    ((0.57, 0.56), (0.62, 0.56), GREEN),
                    ((0.78, 0.61), (0.83, 0.64), GREEN),
                    ((0.78, 0.49), (0.83, 0.44), ORANGE)]:
        arrow(ax2, a, b, c, lw=1.7)

    box(ax2, (0.36, 0.17), (0.29, 0.16),
        "5. AGENT XEM KẾT QUẢ TỪ LEAN\nCòn lượt xử lý: sửa cách chứng minh hoặc tìm thêm thông tin\nThiếu dữ liệu trong hồ sơ: yêu cầu người dùng bổ sung",
        "FFFFFF", ORANGE, fontsize=8.6)
    arrow(ax2, (0.86, 0.37), (0.65, 0.29), ORANGE, rad=-0.05, lw=1.7)
    arrow(ax2, (0.36, 0.25), (0.11, 0.48), ORANGE, rad=-0.25, lw=1.8)
    ax2.text(0.22, 0.31, "thử lại nhưng không vượt số lần cho phép", fontsize=7.8,
             color=f"#{ORANGE}", ha="center", fontweight="bold")

    box(ax2, (0.70, 0.16), (0.12, 0.16), "THIẾU THÔNG TIN\n→ nói rõ cần bổ sung\ntài liệu nào", LIGHT_BLUE, BLUE, fontsize=8.2)
    box(ax2, (0.85, 0.16), (0.12, 0.16), "HỆ THỐNG CHƯA\nXỬ LÝ ĐƯỢC\n→ người phụ trách kiểm tra", LIGHT_ORANGE, RED, fontsize=8.0)
    arrow(ax2, (0.65, 0.25), (0.70, 0.25), BLUE, lw=1.4)
    arrow(ax2, (0.65, 0.22), (0.85, 0.24), RED, rad=-0.05, lw=1.4)

    ax2.text(0.035, 0.035,
             "Lean chưa kiểm tra xong không có nghĩa doanh nghiệp không đủ điều kiện. Khi chưa có kết quả rõ ràng, hệ thống phải nói phần còn thiếu hoặc nhờ người phụ trách kiểm tra.",
             fontsize=8.5, color=f"#{RED}", fontweight="bold")

    fig.suptitle(
        "Kiến trúc Agentic RAG + Lean 4 cho hỗ trợ giải trình thuế GTGT đối với hoạt động xuất khẩu",
        fontsize=18, color=f"#{NAVY}", fontweight="bold", y=0.995,
    )
    fig.savefig(ARCH_V2_PNG, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(ARCH_V2_SVG, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_report() -> None:
    doc = setup_document(
        "BÁO CÁO TỔNG QUAN LÝ THUYẾT\nVÀ YÊU CẦU NGHIỆP VỤ",
        "RAG, Agentic RAG, AI Agent và Lean 4 trong bài toán thuế GTGT đối với hoạt động xuất khẩu",
    )
    add_toc_placeholder(doc)

    doc.add_heading("TÓM TẮT ĐIỀU HÀNH", level=1)
    doc.add_paragraph(
        "Báo cáo xác lập nền tảng lý thuyết và yêu cầu nghiệp vụ cho hệ thống hỗ trợ kiểm tra, "
        "hoàn thiện giải trình thuế giá trị gia tăng (GTGT) đối với hoạt động xuất khẩu. Thiết kế "
        "được chốt theo hướng có thể đánh giá: RAG cung cấp căn cứ có thể truy vết; AI Agent điều "
        "phối việc phân rã câu hỏi, truy xuất và đối chiếu hồ sơ; Agentic RAG cho phép lặp có kiểm "
        "soát khi hồ sơ phức tạp; Lean 4 chỉ kiểm chứng các điều kiện đã được hình thức hóa và duyệt."
    )
    add_note(
        doc,
        "Kết luận chính",
        "Kiến trúc phù hợp không phải là một tác nhân tự quyết định pháp lý. Đây là quy trình hỗ trợ "
        "có giới hạn, trong đó mọi nhận định quan trọng phải liên kết tới nguồn luật, phiên bản luật, "
        "bằng chứng hồ sơ và—khi áp dụng—kết quả Lean. Trạng thái thiếu dữ liệu được giữ là unknown, "
        "không được ngầm coi là đã đáp ứng hoặc không đáp ứng điều kiện.",
        LIGHT_GREEN,
    )
    add_bullets(doc, [
        "Phạm vi nghiệp vụ: điều kiện thuế suất 0%, khấu trừ thuế GTGT đầu vào, hoàn thuế cho hàng hóa/dịch vụ xuất khẩu và chuẩn bị nội dung giải trình có căn cứ.",
        "Người dùng mục tiêu: kế toán thuế, bộ phận pháp chế/tuân thủ và người lập hồ sơ xuất khẩu; kết quả không thay thế ý kiến chuyên gia hay quyết định của cơ quan thuế.",
        "Đơn vị xử lý trung tâm: một ca nghiệp vụ tại một thời điểm áp dụng luật, gồm câu hỏi, bộ tài liệu, các thực thể giao dịch và chuỗi bằng chứng liên kết.",
        "Đầu ra an toàn: đáp ứng có điều kiện; chưa đủ bằng chứng; có mâu thuẫn; ngoài phạm vi; hoặc cần người có thẩm quyền rà soát.",
    ])

    doc.add_heading("1. MỤC TIÊU, ĐỐI TƯỢNG VÀ PHƯƠNG PHÁP", level=1)
    doc.add_heading("1.1. Bài toán nghiên cứu", level=2)
    doc.add_paragraph(
        "Hồ sơ xuất khẩu không chỉ chứa văn bản luật và một vài chứng từ độc lập. Kết luận thường phụ "
        "thuộc vào quan hệ giữa hợp đồng, hóa đơn, tờ khai hải quan, giao nhận/vận tải, thanh toán, kê "
        "khai thuế và thời điểm hiệu lực của quy định. Sai sót có thể nằm ở dữ liệu thiếu, thông tin "
        "không khớp, căn cứ hết hiệu lực hoặc suy luận vượt quá chứng cứ. Vì vậy, hệ thống phải xử lý "
        "đồng thời bài toán truy xuất pháp luật, đối chiếu hồ sơ, quản trị bất định và truy vết kết quả."
    )
    doc.add_heading("1.2. Câu hỏi nghiên cứu trung tâm", level=2)
    add_note(
        doc,
        "RQ",
        "Việc tích hợp Agentic RAG với kiểm chứng hình thức bằng Lean 4 có cải thiện độ chính xác của "
        "truy xuất/câu trả lời, khả năng phát hiện thiếu hoặc mâu thuẫn bằng chứng, khả năng từ chối kết "
        "luận phù hợp và khả năng truy vết cho giải trình thuế GTGT đối với hoạt động xuất khẩu, so với "
        "RAG thông thường hay không?",
        LIGHT_BLUE,
    )
    doc.add_heading("1.3. Phương pháp", level=2)
    add_numbered(doc, [
        "Tổng hợp lý thuyết từ bài báo gốc về RAG/DPR, nghiên cứu Adaptive-RAG, khảo sát Agentic RAG, tài liệu đánh giá RAG và tài liệu chính thức của Lean 4.",
        "Đối chiếu nguồn pháp luật đang lưu trong resources/references, ưu tiên Luật Thuế GTGT, nghị định/thông tư hướng dẫn, quản lý thuế, hóa đơn và hải quan.",
        "Mô hình hóa nghiệp vụ theo tác nhân, ca sử dụng, cấu trúc hồ sơ, chuỗi bằng chứng, trạng thái bằng chứng và yêu cầu hệ thống.",
        "Tách ranh giới kiểm chứng: truy xuất/phiên bản, trích xuất dữ kiện, hình thức hóa quy tắc, chứng minh Lean và sinh giải trình được đánh giá độc lập.",
    ])

    doc.add_heading("2. CƠ SỞ LÝ THUYẾT", level=1)
    doc.add_heading("2.1. Retrieval-Augmented Generation (RAG)", level=2)
    doc.add_paragraph(
        "RAG kết hợp bộ nhớ tham số của mô hình sinh với bộ nhớ ngoài có thể cập nhật và kiểm tra. "
        "Trong công trình nền tảng của Lewis và cộng sự, truy vấn được mã hóa, các đoạn liên quan được "
        "lấy từ chỉ mục, sau đó mô hình sinh điều kiện hóa trên câu hỏi và ngữ cảnh truy xuất. DPR cho "
        "thấy truy xuất ngữ nghĩa có thể dùng hai bộ mã hóa cho câu hỏi và đoạn văn, nhưng trong miền "
        "pháp luật vẫn cần truy xuất từ khóa để giữ số hiệu, điều/khoản, cụm từ chuyên ngành và tên chứng từ."
    )
    add_table(doc, ["Thành phần", "Vai trò trong đề tài", "Rủi ro cần kiểm soát"], [
        ("Kho nguồn có phiên bản", "Lưu văn bản, hiệu lực, quan hệ sửa đổi/thay thế, vị trí trích dẫn", "Dùng nhầm phiên bản hoặc mất ngữ cảnh điều/khoản"),
        ("Chia đoạn và metadata", "Tạo đơn vị truy xuất nhưng giữ cấu trúc văn bản", "Cắt rời ngoại lệ, định nghĩa hoặc dẫn chiếu"),
        ("Truy xuất lai", "Kết hợp BM25/từ khóa với embedding và xếp hạng lại", "Đoạn gần nghĩa nhưng sai văn bản/thời điểm"),
        ("Tạo ngữ cảnh", "Chỉ đưa các đoạn đủ căn cứ vào mô hình sinh", "Nhiễu ngữ cảnh, mất trích dẫn, vượt cửa sổ"),
        ("Sinh câu trả lời", "Tổng hợp nhận định, thiếu sót và gợi ý giải trình", "Khẳng định vượt nguồn hoặc gắn sai trích dẫn"),
        ("Kiểm tra đầu ra", "Đối chiếu từng mệnh đề với nguồn và phiên bản", "Tin vào độ trôi chảy thay vì bằng chứng"),
    ], widths=[3.4, 7.2, 6.2])
    doc.add_paragraph(
        "Đối với đề tài, RAG không được hiểu là cơ chế bảo đảm tính đúng. Nó là cách cung cấp căn cứ "
        "và khả năng cập nhật tri thức. Chất lượng cuối cùng còn phụ thuộc độ bao phủ của kho luật, truy "
        "xuất, trích xuất hồ sơ, cách tổng hợp và kiểm tra mệnh đề–trích dẫn."
    )

    doc.add_heading("2.2. AI Agent", level=2)
    doc.add_paragraph(
        "AI Agent là thành phần phần mềm nhận mục tiêu và trạng thái hiện tại, lựa chọn hành động, gọi "
        "công cụ, quan sát kết quả rồi cập nhật kế hoạch. Trong hệ thống này, năng lực tác nhân không "
        "đồng nghĩa với quyền tự chủ không giới hạn. Bộ điều phối phải bị ràng buộc bởi danh sách công "
        "cụ, số bước, thời gian, ngân sách token/chi phí, lược đồ dữ liệu và các điểm dừng bắt buộc."
    )
    add_table(doc, ["Khả năng", "Biểu hiện trong bài toán", "Ràng buộc"], [
        ("Nhận biết", "Đọc câu hỏi, loại hồ sơ, thời điểm áp dụng, dữ liệu đã có", "Không suy đoán tài liệu chưa được cung cấp"),
        ("Lập kế hoạch", "Tách kiểm tra thuế suất 0%, khấu trừ, hoàn thuế và giải trình", "Kế hoạch mẫu, tối đa số bước đã cấu hình"),
        ("Sử dụng công cụ", "Truy xuất, OCR, so khớp, tính toán, gọi Lean", "Danh sách cho phép, đầu vào/đầu ra có kiểu"),
        ("Bộ nhớ trạng thái", "Lưu thực thể, liên kết và kết quả kiểm tra trong một ca", "Không trộn dữ liệu giữa doanh nghiệp/ca"),
        ("Tự kiểm tra", "Kiểm tra đủ căn cứ, mâu thuẫn và trích dẫn trước khi trả lời", "Cổng quyết định tất định ở cuối"),
        ("Dừng/chuyển người", "Từ chối kết luận hoặc yêu cầu rà soát", "Điều kiện dừng rõ, không lặp vô hạn"),
    ], widths=[3.2, 7.4, 6.2])

    doc.add_heading("2.3. Agentic RAG", level=2)
    doc.add_paragraph(
        "Agentic RAG bổ sung lớp điều khiển chủ động lên đường ống RAG: quyết định khi nào cần truy xuất, "
        "truy xuất nguồn nào, có cần viết lại truy vấn hay truy xuất nhiều bước không, bằng chứng đã đủ "
        "chưa và công cụ nào cần gọi tiếp. Adaptive-RAG cung cấp một tiền lệ quan trọng: không phải câu "
        "hỏi nào cũng cần quy trình phức tạp; chọn chiến lược theo độ phức tạp giúp cân bằng độ chính xác "
        "và chi phí."
    )
    add_table(doc, ["Tiêu chí", "RAG", "Agentic RAG"], [
        ("Luồng xử lý", "Tuyến tính, thường một lượt", "Có định tuyến, lặp, điều kiện dừng"),
        ("Truy vấn", "Truy vấn ban đầu", "Phân rã/viết lại theo bằng chứng còn thiếu"),
        ("Công cụ", "Chủ yếu bộ truy xuất + LLM", "Truy xuất, kiểm tra dữ liệu, tính toán, Lean"),
        ("Hồ sơ nhiều tài liệu", "Ghép ngữ cảnh", "Xây chuỗi bằng chứng và kiểm tra liên kết"),
        ("Rủi ro", "Bỏ sót nguồn hoặc trả lời vượt căn cứ", "Lặp sai, gọi công cụ dư, khuếch đại lỗi"),
        ("Biện pháp", "Cổng trích dẫn và từ chối", "Thêm ngân sách bước, trạng thái có kiểu, nhật ký và cổng đầu ra"),
    ], widths=[3.2, 6.8, 6.8])
    doc.add_paragraph(
        "Các mẫu reflection, planning, tool use và multi-agent là lựa chọn thiết kế, không phải tất cả đều "
        "bắt buộc. Với đồ án, một bộ điều phối đơn có trạng thái rõ và công cụ giới hạn là cấu hình mặc "
        "định; nhiều tác nhân chỉ nên được thêm nếu thực nghiệm chứng minh lợi ích."
    )

    doc.add_heading("2.4. Lean 4 và kiểm chứng hình thức", level=2)
    doc.add_paragraph(
        "Lean 4 là ngôn ngữ lập trình hàm và trình chứng minh tương tác dựa trên lý thuyết kiểu phụ thuộc. "
        "Theo cách nhìn proposition-as-types, mệnh đề là kiểu và chứng minh là một hạng có kiểu đó. Tactic "
        "xây dựng proof term; kernel nhỏ kiểm tra proof term. Do đó, hệ thống có thể kiểm tra tất định rằng "
        "một kết luận hình thức có suy ra từ giả thiết và quy tắc đã mã hóa hay không."
    )
    add_table(doc, ["Đối tượng", "Ánh xạ trong đề tài", "Điều được/không được xác nhận"], [
        ("Quy tắc Lean", "Quy định đã được người có chuyên môn duyệt, gắn nguồn và phiên bản", "Xác nhận cú pháp/kiểu; không xác nhận bản dịch pháp lý tự nó trung thành"),
        ("Giả thiết", "Dữ kiện hồ sơ đã trích xuất và liên kết", "Lean dùng giả thiết; không xác thực chứng từ thật/giả"),
        ("Nghĩa vụ chứng minh", "Kết luận hẹp cần kiểm tra", "Chứng minh tính suy dẫn trong phạm vi biểu diễn"),
        ("Proof term + kernel", "Tạo/kiểm tra chứng minh", "PASS có nghĩa chứng minh hợp lệ với môi trường đã khóa"),
        ("Cổng phát hành", "Kiểm tra nguồn, phiên bản, theorem/case ID, axiom, sorry/admit", "Ngăn dùng nhầm proof; vẫn cần kiểm tra lời giải thích tự nhiên"),
    ], widths=[3.2, 6.7, 6.9])
    add_note(
        doc,
        "Ranh giới bắt buộc",
        "Lean không chứng minh rằng OCR đúng, truy xuất đầy đủ, quy tắc tiếng Việt được dịch đúng, chứng "
        "từ xác thực hoặc câu trả lời tự nhiên hoàn toàn đúng. Lean chỉ chứng minh tính suy dẫn của phát "
        "biểu đã mã hóa từ các giả thiết đã mã hóa. Vì vậy cần đánh giá riêng lỗi nguồn, lỗi trích xuất, lỗi "
        "hình thức hóa, lỗi chứng minh và lỗi sinh câu trả lời.",
        LIGHT_ORANGE,
    )

    doc.add_heading("2.5. Khảo sát công nghệ và khung tham chiếu", level=2)
    doc.add_paragraph(
        "Bốn công nghệ dưới đây không nằm cùng một tầng. Agentic RAG điều phối nghiệp vụ và truy xuất; "
        "LegalLean cung cấp khái niệm biểu diễn suy luận pháp lý; LeanDojo-v2 là hạ tầng nghiên cứu và "
        "proof search; APOLLO là quy trình sửa proof dựa trên phản hồi của Lean. Vì vậy, bảng đánh giá "
        "không chọn một công nghệ duy nhất để thay thế tất cả, mà xác định vai trò và mức thử nghiệm phù hợp."
    )

    doc.add_heading("2.5.1. Agentic RAG", level=3)
    doc.add_paragraph(
        "Agentic RAG là lớp điều phối của luồng xử lý hồ sơ. Nó phân rã câu hỏi, định tuyến tới nguồn/công "
        "cụ, viết lại truy vấn theo khoảng trống bằng chứng và dừng khi đã đủ căn cứ hoặc hết ngân sách. "
        "Trong đề tài, cấu hình mặc định là một bộ điều phối có trạng thái và giới hạn rõ; mô hình nhiều "
        "agent chỉ là giả thuyết cần ablation, không phải yêu cầu kiến trúc."
    )
    add_bullets(doc, [
        "Tương thích cao với truy xuất nhiều văn bản và đối chiếu chuỗi hợp đồng–hóa đơn–hải quan–vận tải–thanh toán.",
        "Chi phí tích hợp trung bình: cần workflow state, schema công cụ, ngân sách bước, timeout, điều kiện dừng và nhật ký.",
        "Quyết định: dùng trong lõi của cấu hình Agentic RAG và Agentic RAG + Lean; không cho phép tự sửa quy tắc pháp luật đã duyệt.",
    ])

    doc.add_heading("2.5.2. LeanDojo-v2", level=3)
    doc.add_paragraph(
        "LeanDojo-v2 là framework đầu-cuối cho nghiên cứu prover Lean 4: tracing kho mã, tạo dữ liệu theorem/"
        "proof state/tactic/premise, quản lý tập dữ liệu động, huấn luyện hoặc gọi prover và tương tác proof "
        "search qua Pantograph. Nó phù hợp khi đề tài đã có theorem và proof obligation; nó không đọc hồ sơ "
        "thuế thô, không dịch quy định tiếng Việt và không xác nhận tính trung thành ngữ nghĩa của formalization."
    )
    add_bullets(doc, [
        "Tương thích trung bình: phù hợp tầng proof engineering nhưng cần kiểm tra phiên bản Lean/Pantograph và định dạng project.",
        "Chi phí tích hợp cao: Python/ML stack, tracing, dữ liệu proof, checkpoint hoặc API inference; huấn luyện cục bộ có thể cần GPU.",
        "Quyết định: thử nghiệm có giới hạn cho tracing, benchmark, premise retrieval và proof search sau khi Lean runtime/tactic tất định đã ổn định.",
    ])

    doc.add_heading("2.5.3. APOLLO", level=3)
    doc.add_paragraph(
        "APOLLO (Automated PrOof repair via LLM and Lean cOllaboration) là framework agentic sửa proof Lean. "
        "Nó dùng lỗi từ Lean REPL để làm sạch cú pháp, cô lập sub-lemma lỗi, thử solver tự động, gọi LLM trên "
        "các goal còn mở, ghép proof và kiểm tra lại. APOLLO dùng `sorry` như trạng thái trung gian để đánh dấu "
        "sub-problem, nhưng bước lắp ráp cuối kiểm tra không còn `sorry` hoặc `admit`."
    )
    add_bullets(doc, [
        "Tương thích trung bình: có thể nhận proof sketch của nghĩa vụ VAT đã được tạo đúng, nhưng benchmark công bố chủ yếu là toán học miniF2F.",
        "Chi phí tích hợp trung bình–cao: Lean REPL, nhiều bước sửa, LLM/API hoặc model cục bộ, giới hạn recursion và kiểm soát artifact.",
        "Quyết định: thí nghiệm phụ cho proof repair; không cho APOLLO đọc hồ sơ thô, thay theorem, thay rule version hoặc quyết định ý nghĩa pháp lý.",
        "Cổng phát hành của dự án vẫn bắt buộc build sạch, không `sorry`/`admit`, kiểm tra axiom và khóa proof–case–rule identity.",
    ])

    doc.add_heading("2.5.4. LegalLean", level=3)
    doc.add_paragraph(
        "LegalLean là kiến trúc tham chiếu cho suy luận pháp lý kiểm chứng bằng Lean 4. Các kiểu như "
        "`LegalRule`, `EvidenceFor`, `DefeasiblyHolds`, `FormalisationBoundary` và "
        "`RequiresHumanDetermination` hữu ích để biểu diễn nguồn gốc bằng chứng, khả năng bị đánh bại và "
        "ranh giới giữa phần hình thức với phần cần phán đoán của con người. Tuy nhiên, đây không phải mô-đun "
        "VAT Việt Nam có thể cài và dùng trực tiếp."
    )
    add_bullets(doc, [
        "Tương thích trung bình–cao ở tầng mô hình khái niệm; thấp hơn ở tầng domain vì authority, temporal semantics và case studies chưa hướng tới thuế Việt Nam.",
        "Chi phí tích hợp trung bình–cao: cần authority Việt Nam, typed rule/source IDs, hiệu lực thời gian và lowering từ Legal IR sang predicate VAT thực.",
        "Quyết định: chọn lọc abstraction và mẫu kiến trúc; không nhập nguyên framework, không dùng kết luận placeholder và không coi mapping đề xuất là hành vi đã triển khai.",
    ])

    doc.add_heading("2.5.5. Bảng đánh giá và quyết định thử nghiệm", level=3)
    doc.add_paragraph(
        "Chi phí dưới đây là ước lượng tương đối cho prototype: thấp = hầu như không thêm runtime mới; "
        "trung bình = cần adapter/workflow và kiểm thử tích hợp; cao = thêm stack ML, dữ liệu/checkpoint, GPU/API "
        "hoặc gánh nặng tương thích phiên bản đáng kể."
    )
    add_table(doc,
        ["Công nghệ", "Vai trò phù hợp", "Tương thích", "Chi phí", "Quyết định"],
        [
            ("Agentic RAG", "Điều phối truy xuất, công cụ và chuỗi bằng chứng", "Cao", "Trung bình", "Thành phần lõi của cấu hình B và C"),
            ("Lean 4 trực tiếp", "Kernel kiểm chứng và tactic tất định", "Cao", "Thấp–trung bình", "Runtime bắt buộc cho nhánh Lean"),
            ("LegalLean", "Khung rule/evidence/defeasibility/formalisation boundary", "Trung bình–cao", "Trung bình–cao", "Chọn lọc abstraction; không dùng nguyên khối"),
            ("LeanDojo-v2", "Tracing, dataset, premise retrieval, benchmark và proof search", "Trung bình", "Cao", "PoC có giới hạn sau runtime lõi"),
            ("APOLLO", "Sửa proof dựa trên compiler feedback", "Trung bình", "Trung bình–cao", "Thử nghiệm phụ trên tập proof lỗi"),
        ], widths=[2.7, 5.4, 2.4, 2.7, 4.0]
    )
    add_note(
        doc,
        "Quyết định thực nghiệm",
        "Ba đối chứng chính vẫn là RAG, Agentic RAG và Agentic RAG + Lean 4. LeanDojo-v2 và APOLLO chỉ "
        "tham gia thí nghiệm phụ trong tầng proof: tactic tất định → base model/feedback → proof search hoặc "
        "proof repair. Cách tách này tránh biến công cụ prover thành một phương án đối chứng nghiệp vụ mới.",
        LIGHT_GREEN,
    )

    doc.add_heading("3. PHÂN TÍCH YÊU CẦU NGHIỆP VỤ", level=1)
    doc.add_heading("3.1. Tác nhân và ca sử dụng", level=2)
    add_table(doc, ["Tác nhân", "Nhu cầu", "Đầu ra cần nhận"], [
        ("Kế toán thuế", "Rà soát hồ sơ trước kê khai/hoàn thuế", "Danh sách đủ/thiếu/mâu thuẫn; căn cứ; việc cần bổ sung"),
        ("Pháp chế/tuân thủ", "Kiểm tra lập luận và phiên bản pháp luật", "Chuỗi mệnh đề–nguồn–bằng chứng; ngoại lệ; dấu vết kiểm tra"),
        ("Người lập giải trình", "Soạn bản giải trình có cấu trúc", "Bản nháp bám nguồn, không che giấu điểm chưa chắc chắn"),
        ("Người duyệt", "Đánh giá kết quả trước sử dụng", "Báo cáo tóm tắt, cảnh báo, proof ID và nhật ký"),
        ("Quản trị hệ thống", "Cập nhật kho luật và quy tắc", "Lịch sử phiên bản, phê duyệt, khả năng quay lại phiên bản"),
    ], widths=[3.0, 7.0, 6.8])
    doc.add_paragraph("Các ca sử dụng chính gồm:")
    add_bullets(doc, [
        "Xác định quy định và phiên bản áp dụng tại thời điểm giao dịch/kỳ thuế.",
        "Kiểm tra bộ hồ sơ điều kiện áp dụng thuế suất 0% cho hàng hóa/dịch vụ xuất khẩu.",
        "Kiểm tra điều kiện khấu trừ thuế GTGT đầu vào và các chứng từ thanh toán liên quan.",
        "Kiểm tra điều kiện, phép tính và giới hạn của hoàn thuế đối với xuất khẩu.",
        "Đối chiếu chủ thể, hàng hóa/dịch vụ, số lượng, giá trị, tiền tệ, ngày tháng và mã tham chiếu giữa chứng từ.",
        "Phát hiện thiếu, xung đột, ngoài phạm vi; yêu cầu bổ sung hoặc chuyển người rà soát.",
        "Tạo bản nháp giải trình với trích dẫn điều/khoản và liên kết tới chứng từ hồ sơ.",
    ])

    doc.add_heading("3.2. Cấu trúc hồ sơ nghiệp vụ", level=2)
    add_table(doc, ["Nhóm", "Tài liệu/dữ liệu điển hình", "Trường liên kết quan trọng"], [
        ("Định danh và kỳ thuế", "MST, đơn vị, kỳ kê khai, đề nghị hoàn, tài khoản ngân hàng", "MST, kỳ, ngày nộp, hồ sơ ID"),
        ("Hợp đồng/giao dịch", "Hợp đồng với bên nước ngoài, phụ lục, điều khoản giao nhận/thanh toán", "Số hợp đồng, đối tác, Incoterms, tiền tệ"),
        ("Hóa đơn/kế toán", "Hóa đơn đầu vào/đầu ra, bảng kê, sổ kế toán", "Số hóa đơn, ngày, dòng hàng, tiền thuế, nhà cung cấp"),
        ("Hải quan", "Tờ khai, thông quan, mã hàng, cửa khẩu", "Số tờ khai, ngày, mã HS, lượng, trị giá"),
        ("Vận tải/giao nhận", "Vận đơn, phiếu đóng gói, giao nhận, bảo hiểm nếu có", "B/L, container, lô hàng, trọng lượng, địa điểm"),
        ("Thanh toán", "Ủy nhiệm chi, sao kê, SWIFT, đối trừ được phép", "Payment ref, tài khoản, người trả/nhận, số tiền, ngày"),
        ("Thuế và pháp luật", "Luật, nghị định, thông tư, văn bản sửa đổi; kê khai", "Văn bản ID, điều/khoản, hiệu lực, kỳ"),
        ("Giải trình và kiểm tra", "Công văn, yêu cầu bổ sung, biên bản, phản hồi", "Yêu cầu ID, claim ID, evidence ID"),
    ], widths=[2.8, 7.2, 6.8])

    doc.add_heading("3.3. Chuỗi bằng chứng", level=2)
    doc.add_paragraph(
        "Chuỗi bằng chứng là đồ thị liên kết giữa một nhận định cần chứng minh và các nguồn hỗ trợ hoặc "
        "phản bác. Mỗi cạnh phải chỉ rõ loại quan hệ và khóa đối chiếu; không được ghép tài liệu chỉ vì "
        "cùng xuất hiện trong một hồ sơ. Chuỗi tối thiểu cho một giao dịch hàng hóa xuất khẩu có thể biểu "
        "diễn như sau:"
    )
    add_note(
        doc,
        "Mẫu chuỗi",
        "Quy định có hiệu lực → điều kiện cần kiểm tra → hợp đồng/đơn hàng → hóa đơn bán hàng → tờ khai "
        "hải quan → đóng gói/vận đơn/giao nhận → thanh toán qua ngân hàng → hóa đơn đầu vào và hạch toán → "
        "kê khai/đề nghị hoàn → mệnh đề giải trình. Mỗi bước lưu source_id, evidence_id, vị trí, giá trị chuẩn "
        "hóa và mức chắc chắn.",
        LIGHT_GREEN,
    )
    add_table(doc, ["Trạng thái", "Ý nghĩa", "Hành vi hệ thống"], [
        ("present", "Có bằng chứng được nhận diện và liên kết", "Tiếp tục kiểm tra tính nhất quán/chất lượng"),
        ("absent", "Đã xác định tài liệu/trường bắt buộc không có", "Báo thiếu; không tạo giả thiết dương"),
        ("unknown", "Chưa đủ dữ liệu để biết có hay không/đúng hay không", "Hỏi bổ sung hoặc chuyển người; không coi là absent/present"),
        ("notApplicable", "Điều kiện được xác nhận là không áp dụng", "Phải lưu lý do và căn cứ cho việc không áp dụng"),
        ("conflicting", "Hai hoặc nhiều nguồn không nhất quán", "Nêu rõ trường và tài liệu xung đột; chặn kết luận liên quan"),
    ], widths=[3.0, 7.0, 6.8])

    doc.add_heading("3.4. Quy tắc đối chiếu cốt lõi", level=2)
    add_table(doc, ["Loại đối chiếu", "Ví dụ", "Kết quả"], [
        ("Chủ thể", "Tên/MST bên bán, bên mua, người trả/nhận tiền", "Khớp / lệch / thiếu / chưa xác định"),
        ("Giao dịch", "Hợp đồng–hóa đơn–tờ khai–vận đơn cùng lô hàng", "Liên kết chắc chắn hoặc cần rà soát"),
        ("Giá trị", "Số tiền, tiền tệ, thuế, chênh lệch cho phép", "Khớp; chênh lệch có/không có giải thích"),
        ("Số lượng/hàng hóa", "Mô tả, mã HS, lượng, trọng lượng", "Khớp theo dòng hàng hoặc xung đột"),
        ("Thời gian", "Ngày hóa đơn, mở tờ khai, giao hàng, thanh toán", "Thứ tự hợp lý; ngoại lệ; ngoài kỳ"),
        ("Hiệu lực pháp luật", "Ngày giao dịch/kỳ thuế so với hiệu lực văn bản", "Chọn đúng phiên bản; báo văn bản thay thế"),
        ("Nguồn–nhận định", "Mỗi câu kết luận gắn điều/khoản và đoạn hỗ trợ", "Được hỗ trợ đầy đủ/một phần/không hỗ trợ"),
    ], widths=[3.0, 7.3, 6.5])

    doc.add_heading("4. ĐẶC TẢ YÊU CẦU HỆ THỐNG", level=1)
    doc.add_heading("4.1. Yêu cầu chức năng", level=2)
    add_table(doc, ["Mã", "Yêu cầu", "Mức ưu tiên", "Tiêu chí chấp nhận sơ bộ"], [
        ("FR-01", "Nạp PDF/ảnh/bảng tính và lưu bản gốc có băm định danh", "Bắt buộc", "Không làm mất tệp; truy vết được tới trang/vùng"),
        ("FR-02", "Quản lý nguồn luật, hiệu lực, sửa đổi/thay thế và vị trí trích dẫn", "Bắt buộc", "Mỗi căn cứ có source/version ID"),
        ("FR-03", "Truy xuất lai và xếp hạng lại theo câu hỏi/thời điểm", "Bắt buộc", "Trả top-k cùng điểm và metadata"),
        ("FR-04", "Trích xuất thực thể/trường hồ sơ kèm provenance", "Bắt buộc", "Mỗi giá trị có evidence ID và vị trí"),
        ("FR-05", "Xây đồ thị hồ sơ và đối chiếu chéo", "Bắt buộc", "Hiển thị khóa liên kết và mâu thuẫn"),
        ("FR-06", "Lập kế hoạch/gọi công cụ có giới hạn", "Bắt buộc cho Agentic RAG", "Tuân thủ số bước, thời gian và danh sách công cụ"),
        ("FR-07", "Tạo nghĩa vụ chứng minh và gọi Lean trên ca đủ điều kiện", "Bắt buộc cho cấu hình 3", "Proof/case/rule version liên kết một-một"),
        ("FR-08", "Sinh giải trình bám nguồn và biểu đạt bất định", "Bắt buộc", "Mỗi mệnh đề trọng yếu có căn cứ hoặc nhãn chưa đủ"),
        ("FR-09", "Cổng đầu ra tất định", "Bắt buộc", "Chặn sai nguồn/phiên bản, proof mismatch, thiếu trích dẫn"),
        ("FR-10", "Lưu nhật ký truy vết và xuất báo cáo", "Bắt buộc", "Tái lập được cấu hình, bước và kết quả"),
    ], widths=[1.5, 8.0, 2.4, 5.0])

    doc.add_heading("4.2. Yêu cầu phi chức năng", level=2)
    add_table(doc, ["Nhóm", "Yêu cầu"], [
        ("Độ tin cậy", "Không phát hành kết luận nếu thiếu nguồn, sai phiên bản, mâu thuẫn chưa xử lý hoặc proof không khớp ca."),
        ("Khả năng tái lập", "Khóa corpus snapshot, model/prompt/config, rule version, toolchain Lean và seed khi có."),
        ("Bảo mật", "Phân quyền tối thiểu, tách ca/doanh nghiệp, che dữ liệu nhạy cảm, chống prompt injection từ tài liệu."),
        ("Khả năng giải thích", "Hiển thị điều kiện, bằng chứng, nguồn, trạng thái và lý do dừng/chuyển người."),
        ("Hiệu năng", "Đo p50/p95 latency, số lần gọi công cụ, token và chi phí; có timeout/fallback."),
        ("Bảo trì", "Mô-đun hóa; thay model/vector store mà không đổi hợp đồng dữ liệu nghiệp vụ."),
        ("Quản trị", "Quy trình duyệt nguồn luật và quy tắc Lean; lịch sử thay đổi, người duyệt, thời điểm kích hoạt."),
    ], widths=[3.5, 13.3])

    doc.add_heading("4.3. Hợp đồng đầu vào và đầu ra", level=2)
    add_table(doc, ["Đối tượng", "Trường tối thiểu"], [
        ("Case", "case_id, taxpayer_id đã ẩn danh, tax_period, transaction_type, question, submitted_at"),
        ("Source", "source_id, instrument_no, authority, issued/effective/expiry dates, version, article/clause, file_hash"),
        ("Evidence", "evidence_id, case_id, document_type, page/region, extracted_value, normalized_value, status, confidence, reviewer"),
        ("Claim", "claim_id, text, claim_type, cited_source_ids, cited_evidence_ids, support_status"),
        ("Proof artifact", "proof_id, theorem_hash, rule_version, case_snapshot_hash, toolchain, result, axioms, sorry/admit check"),
        ("Final result", "status, satisfied/unsatisfied/unknown conditions, conflicts, missing items, explanation, citations, proof_id, audit_id"),
    ], widths=[4.0, 12.8])

    doc.add_heading("5. KIẾN TRÚC VÀ QUY TRÌNH DỰ KIẾN", level=1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(ARCH_V2_PNG), width=Inches(6.55))
    doc.add_paragraph(
        "Hình 1. Các thành phần chính và cách Agent gọi Lean 4 trong quá trình xử lý (bản vector được cung cấp riêng).",
        style="Caption VN",
    )
    doc.add_paragraph(
        "Kiến trúc tách luồng ngoại tuyến và trực tuyến. Luồng ngoại tuyến quản trị nguồn luật, chỉ mục và "
        "quy tắc Lean đã duyệt. Luồng trực tuyến xử lý từng hồ sơ, xây gói bằng chứng, gọi công cụ theo "
        "ngân sách, tạo nghĩa vụ chứng minh khi đủ điều kiện rồi đi qua cổng đầu ra. Việc tách này tránh "
        "để mô hình trực tuyến tự sửa quy tắc pháp luật hoặc tự kích hoạt một hình thức hóa chưa được duyệt."
    )
    add_note(
        doc,
        "Lean 4 trong runtime của Agent",
        "Khi ca đủ điều kiện hình thức hóa, Agent không chỉ gọi Lean một lần ở cuối. Trong giới hạn số "
        "vòng, Agent tạo nghĩa vụ chứng minh và tactic/proof ứng viên; Lean runtime elaborate, typecheck và "
        "kernel-check rồi trả PASS, FAIL, open goals và compiler feedback. Agent dùng phản hồi để sửa tactic, "
        "truy xuất thêm bằng chứng hoặc dừng/chuyển người. Agent không được thay theorem hay rule version đã duyệt; "
        "chỉ PASS vượt qua kiểm tra sorry/admit/axiom và identity mới được dùng ở cổng đầu ra.",
        LIGHT_GREEN,
    )
    add_numbered(doc, [
        "Chốt thời điểm nghiệp vụ và ảnh chụp phiên bản kho luật.",
        "Nạp/ẩn danh hồ sơ, OCR và trích xuất trường kèm vị trí nguồn.",
        "Truy xuất căn cứ bằng từ khóa + ngữ nghĩa; kiểm tra số hiệu, điều/khoản và hiệu lực.",
        "Xây đồ thị hồ sơ, liên kết tài liệu theo khóa giao dịch và gán trạng thái bằng chứng.",
        "Phát hiện dữ liệu thiếu, xung đột hoặc ngoài phạm vi; quyết định hỏi bổ sung/chuyển người.",
        "Nếu quy tắc và dữ kiện đủ điều kiện hình thức hóa, chạy vòng Agent ↔ Lean: tạo nghĩa vụ, nhận proof state/compiler feedback, sửa tactic hoặc truy xuất thêm trong giới hạn; nếu không, trả lời bám nguồn kèm giới hạn.",
        "Sinh bản nháp giải trình, sau đó kiểm tra tất định nguồn–phiên bản–trích dẫn–proof–câu trả lời.",
        "Trả kết quả có trạng thái và lưu toàn bộ dấu vết phục vụ kiểm tra/tái lập.",
    ])

    doc.add_heading("6. RỦI RO VÀ BIỆN PHÁP KIỂM SOÁT", level=1)
    add_table(doc, ["Rủi ro", "Hậu quả", "Kiểm soát"], [
        ("Kho luật thiếu/sai phiên bản", "Dùng căn cứ không áp dụng", "Nguồn chính thức, lineage, ngày hiệu lực, corpus snapshot"),
        ("OCR/trích xuất sai", "Giả thiết sai truyền vào suy luận", "Provenance tới trang/vùng, confidence, kiểm tra chéo/người duyệt"),
        ("Truy xuất gần nghĩa nhưng sai điều", "Câu trả lời có vẻ hợp lý nhưng sai căn cứ", "Hybrid retrieval, lọc metadata, citation gate"),
        ("Prompt injection trong hồ sơ", "Tác nhân làm theo chỉ dẫn độc hại", "Coi tài liệu là dữ liệu, tách instruction/data, allowlist công cụ"),
        ("Lặp tác nhân không dừng", "Tăng chi phí/độ trễ, kết quả không ổn định", "Giới hạn bước/thời gian/token, điều kiện dừng"),
        ("Hình thức hóa sai nghĩa", "Lean chứng minh đúng một quy tắc sai", "Quy trình duyệt ngữ nghĩa, kiểm thử đối ví dụ, versioned registry"),
        ("Proof không khớp ca", "Dùng kết quả chứng minh cho dữ liệu khác", "Băm theorem/case/rule, kiểm tra identity tại output gate"),
        ("Ngôn ngữ kết luận quá chắc chắn", "Người dùng hiểu sai mức đảm bảo", "Từ vựng trạng thái chuẩn, bắt buộc nêu giới hạn"),
    ], widths=[4.2, 5.4, 7.2])

    doc.add_heading("7. KẾT LUẬN", level=1)
    doc.add_paragraph(
        "Cơ sở lý thuyết và phân tích nghiệp vụ cho thấy lợi ích kỳ vọng của hệ thống không nằm ở việc "
        "dùng nhiều tác nhân hay Lean cho mọi câu hỏi. Giá trị cần kiểm chứng là: truy xuất đúng hơn, "
        "chuỗi bằng chứng rõ hơn, phát hiện thiếu/mâu thuẫn tốt hơn, từ chối phù hợp hơn và kiểm toán được "
        "kết luận. Kiến trúc đã chốt đủ hẹp để triển khai trong đồ án, nhưng vẫn tách mô-đun để ba cấu hình "
        "đối chứng có thể chạy trên cùng dữ liệu và được đo công bằng."
    )

    doc.add_heading("TÀI LIỆU THAM KHẢO", level=1)
    refs = [
        ("[1] Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.", "https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html"),
        ("[2] Karpukhin et al. (2020), Dense Passage Retrieval for Open-Domain Question Answering.", "https://aclanthology.org/2020.emnlp-main.550/"),
        ("[3] Jeong et al. (2024), Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity.", "https://aclanthology.org/2024.naacl-long.389/"),
        ("[4] Singh et al. (2026), Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG.", "https://arxiv.org/abs/2501.09136"),
        ("[5] Es et al. (2024), RAGAS: Automated Evaluation of Retrieval Augmented Generation.", "https://aclanthology.org/2024.eacl-demo.16/"),
        ("[6] Gao et al. (2023), Enabling Large Language Models to Generate Text with Citations.", "https://aclanthology.org/2023.emnlp-main.398/"),
        ("[7] Lean 4, The Lean Language Reference.", "https://lean-lang.org/doc/reference/latest/"),
        ("[8] Avigad, de Moura, Kong et al., Theorem Proving in Lean 4.", "https://lean-lang.org/theorem_proving_in_lean4/"),
        ("[9] LeanDojo-v2, framework for AI-assisted theorem proving in Lean 4.", "https://github.com/lean-dojo/LeanDojo-v2"),
        ("[10] Ospanov, Farnia, Yousefzadeh (2025), APOLLO: Automated LLM and Lean Collaboration for Advanced Formal Reasoning.", "https://arxiv.org/abs/2505.05758"),
        ("[11] LegalLean, Verified Legal Reasoning in Lean 4.", "https://github.com/edu-ap/legal-lean"),
        ("[12] Quốc hội, Luật Thuế giá trị gia tăng số 48/2024/QH15.", "https://vanban.chinhphu.vn/?classid=1&docid=212476&pageid=27160"),
        ("[13] Chính phủ, Nghị định số 181/2025/NĐ-CP.", "https://vanban.chinhphu.vn/?docid=214336&pageid=27160"),
        ("[14] Bộ Tài chính, Thông tư số 69/2025/TT-BTC.", "https://vanban.chinhphu.vn/?classid=1&docid=214417&pageid=27160"),
        ("[15] Kho tài liệu dự án: resources/references và ví dụ Lean formalization/Article14Clause2.lean.", ""),
    ]
    for label, url in refs:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.left_indent = Cm(0.6)
        if url:
            add_hyperlink(p, label, url)
        else:
            p.add_run(label)

    doc.core_properties.title = "Báo cáo tổng quan lý thuyết và yêu cầu nghiệp vụ – Tuần 02"
    doc.core_properties.author = "Nguyễn Tuấn Minh"
    doc.core_properties.subject = "Agentic RAG + Lean 4 cho VAT xuất khẩu"
    doc.save(REPORT_PATH)


def build_spec() -> None:
    doc = setup_document(
        "ĐẶC TẢ PHẠM VI, BA PHƯƠNG ÁN ĐỐI CHỨNG\nVÀ KẾ HOẠCH ĐÁNH GIÁ",
        "Thiết kế thực nghiệm cho hệ thống hỗ trợ kiểm tra và hoàn thiện giải trình thuế GTGT đối với hoạt động xuất khẩu",
    )
    add_toc_placeholder(doc)

    doc.add_heading("TÓM TẮT QUYẾT ĐỊNH", level=1)
    add_table(doc, ["Hạng mục", "Quyết định chốt"], [
        ("Phạm vi", "Pháp luật Việt Nam; thuế suất 0%, khấu trừ đầu vào, hoàn thuế và giải trình cho hoạt động xuất khẩu."),
        ("Cấu hình 1", "RAG: truy xuất lai một lượt + sinh trả lời + cổng trích dẫn/từ chối."),
        ("Cấu hình 2", "Agentic RAG: điều phối có giới hạn, truy xuất nhiều bước, công cụ đối chiếu hồ sơ; không Lean."),
        ("Cấu hình 3", "Agentic RAG + Lean 4: như cấu hình 2, thêm nghĩa vụ chứng minh và kiểm chứng trên tập ca đủ điều kiện."),
        ("Dữ liệu", "Tối thiểu 60 ca; trong đó 20 ca giữ riêng để đánh giá cuối và ít nhất 20 ca đủ điều kiện hình thức hóa."),
        ("An toàn", "Ít nhất 15 tình huống bảo mật/độ tin cậy; không dùng dữ liệu doanh nghiệp mật."),
        ("Nguyên tắc", "Cùng corpus snapshot, model nền, ngân sách và tập ca; chỉ thay năng lực đặc trưng của cấu hình."),
    ], widths=[4.0, 12.8])

    doc.add_heading("1. PHẠM VI", level=1)
    doc.add_heading("1.1. Mục tiêu", level=2)
    doc.add_paragraph(
        "Xây dựng và đánh giá một hệ thống hỗ trợ người làm nghiệp vụ thuế kiểm tra tính đầy đủ/nhất quán "
        "của hồ sơ, tìm đúng căn cứ pháp luật và soạn bản nháp giải trình có thể truy vết. Hệ thống phải "
        "biểu đạt rõ điều kiện đã được hỗ trợ, điều kiện thiếu hoặc mâu thuẫn và giới hạn của kết quả."
    )
    doc.add_heading("1.2. Nội dung trong phạm vi", level=2)
    add_bullets(doc, [
        "Văn bản pháp luật Việt Nam có liên quan và phiên bản áp dụng theo thời điểm của ca.",
        "Hàng hóa/dịch vụ xuất khẩu: xác định đối tượng, điều kiện thuế suất 0% và hồ sơ liên quan.",
        "Điều kiện khấu trừ thuế GTGT đầu vào, chứng từ thanh toán và liên kết với hoạt động xuất khẩu.",
        "Hoàn thuế đối với xuất khẩu: điều kiện, dữ liệu đầu vào, phép tính/giới hạn được mã hóa trong phạm vi ca mẫu.",
        "Trích xuất và đối chiếu hợp đồng, hóa đơn, hải quan, vận tải/giao nhận, thanh toán, kê khai và giải trình.",
        "Phát hiện bằng chứng thiếu, trạng thái chưa biết, mâu thuẫn nội bộ và căn cứ hết/không đúng hiệu lực.",
        "Sinh bản nháp tiếng Việt có trích dẫn và dấu vết; kiểm chứng Lean cho các quy tắc đủ rõ, đã duyệt.",
    ])
    doc.add_heading("1.3. Đối tượng, thời điểm và giả định", level=2)
    add_table(doc, ["Yếu tố", "Đặc tả"], [
        ("Người dùng", "Kế toán thuế, pháp chế/tuân thủ, người lập và người duyệt giải trình."),
        ("Đơn vị đánh giá", "Một ca = câu hỏi + thời điểm + tập tài liệu + nhãn vàng + danh sách nhận định cần kiểm tra."),
        ("Dữ liệu", "Văn bản công khai, mẫu chứng từ công khai hoặc tình huống tổng hợp đã ẩn danh; không dùng dữ liệu mật."),
        ("Ngôn ngữ", "Đầu vào/đầu ra tiếng Việt; giữ thuật ngữ kỹ thuật cần thiết."),
        ("Mức tự động", "Hỗ trợ ra quyết định; người dùng chịu trách nhiệm duyệt trước khi sử dụng ngoài hệ thống."),
        ("Thời gian", "Mỗi ca khóa một mốc thời gian để chọn đúng phiên bản luật và tình trạng chứng từ."),
    ], widths=[4.0, 12.8])

    doc.add_heading("2. BA PHƯƠNG ÁN ĐỐI CHỨNG", level=1)
    doc.add_heading("2.1. Cấu hình A – RAG", level=2)
    add_bullets(doc, [
        "Một lượt: chuẩn hóa câu hỏi → truy xuất lai top-k → xếp hạng → tạo ngữ cảnh → sinh trả lời.",
        "Có kiểm tra trích dẫn, phiên bản và cơ chế từ chối khi không đủ căn cứ.",
        "Không tự phân rã nhiệm vụ, không truy xuất lặp theo thiếu sót, không dùng đồ thị tác nhân, không gọi Lean.",
        "Vai trò: đối chứng tối thiểu mạnh và có thể triển khai, không phải LLM thuần không nguồn."
    ])
    doc.add_heading("2.2. Cấu hình B – Agentic RAG", level=2)
    add_bullets(doc, [
        "Kế thừa toàn bộ RAG và cổng đầu ra của cấu hình A.",
        "Bộ điều phối phân rã câu hỏi, chọn công cụ, viết lại truy vấn, truy xuất nhiều bước và theo dõi bằng chứng còn thiếu.",
        "Dùng công cụ xác thực schema, so khớp thực thể/số tiền/ngày tháng, lập đồ thị hồ sơ và phát hiện xung đột.",
        "Bị giới hạn số bước, số lần truy xuất, thời gian, token/chi phí; có điều kiện dừng và chuyển người.",
        "Không có kết quả Lean; mọi nhận định vẫn phải bám nguồn và trạng thái bằng chứng."
    ])
    doc.add_heading("2.3. Cấu hình C – Agentic RAG + Lean 4", level=2)
    add_bullets(doc, [
        "Kế thừa nguyên trạng cấu hình B.",
        "Với ca đủ điều kiện, chọn quy tắc Lean đã duyệt, ánh xạ bằng chứng sang giả thiết có kiểu và tạo nghĩa vụ chứng minh.",
        "Ưu tiên tactic tất định; có thể thử proof search có giới hạn ở giai đoạn nghiên cứu nhưng không thay đổi theorem/rule đã duyệt.",
        "Cổng phát hành yêu cầu build sạch, không sorry/admit, không axiom ngoài danh sách cho phép, proof/case/rule/version khớp và câu trả lời thống nhất với kết quả.",
        "Lean FAIL/UNKNOWN không đồng nghĩa doanh nghiệp không đủ điều kiện pháp lý; nó chỉ nói kết luận chưa được chứng minh trong mô hình hiện tại."
    ])

    doc.add_heading("2.4. Ma trận khác biệt được phép", level=2)
    add_table(doc, ["Thành phần", "A: RAG", "B: Agentic RAG", "C: Agentic RAG + Lean"], [
        ("Corpus/phiên bản", "Giống", "Giống", "Giống"),
        ("Model sinh chính", "Giống", "Giống", "Giống"),
        ("Retriever/reranker", "Giống", "Giống; được gọi lặp", "Giống; được gọi lặp"),
        ("Cổng trích dẫn/từ chối", "Có", "Có", "Có"),
        ("Lập kế hoạch/định tuyến", "Không", "Có, giới hạn", "Có, giới hạn"),
        ("Công cụ đối chiếu hồ sơ", "Tiền xử lý cố định", "Có, gọi theo kế hoạch", "Có, gọi theo kế hoạch"),
        ("Kho quy tắc Lean", "Không", "Không", "Có, chỉ bản đã duyệt"),
        ("Kiểm chứng Lean", "Không", "Không", "Có trên tập đủ điều kiện"),
        ("Ngân sách", "Đặt trần tương ứng", "Công bố cả giới hạn và mức dùng", "Công bố thêm thời gian Lean"),
    ], widths=[4.0, 4.0, 4.4, 4.4])
    add_note(
        doc,
        "Nguyên tắc công bằng",
        "Không thay đồng thời model, corpus, prompt, retriever và kiến trúc. Cấu hình B chỉ thêm điều phối; "
        "cấu hình C chỉ thêm nhánh Lean trên cùng đầu ra bằng chứng của B. Nếu ngân sách thực tế khác nhau, "
        "báo cáo cả chất lượng và đường biên chất lượng–chi phí.",
        LIGHT_GREEN,
    )

    doc.add_heading("3. THIẾT KẾ BỘ CA VÀ NHÃN VÀNG", level=1)
    doc.add_heading("3.1. Cấu trúc tập dữ liệu", level=2)
    add_table(doc, ["Tập", "Quy mô tối thiểu", "Mục đích", "Quy tắc sử dụng"], [
        ("Phát triển", "40 ca", "Thiết kế prompt, schema, quy tắc và chọn tham số", "Được xem nhãn và phân tích lỗi; chia nhỏ train/dev nếu cần"),
        ("Giữ riêng", "20 ca", "Đánh giá cuối cùng", "Không dùng để sửa prompt/rule/ngưỡng; chỉ mở sau khi khóa cấu hình"),
        ("Đủ điều kiện Lean", "≥20 ca, nằm trong 60", "Đánh giá nhánh hình thức", "Có quy tắc duyệt và ánh xạ giả thiết; phân bố ở cả phát triển/giữ riêng"),
        ("An toàn/độ tin cậy", "≥15 tình huống", "Prompt injection, quyền, phiên bản, lỗi phụ thuộc, khôi phục", "Chạy riêng và báo cáo pass/fail theo kịch bản"),
    ], widths=[3.2, 3.0, 5.6, 5.0])
    doc.add_heading("3.2. Phân tầng ca", level=2)
    add_bullets(doc, [
        "Theo nhiệm vụ: thuế suất 0%; khấu trừ đầu vào; hoàn thuế; giải trình tổng hợp.",
        "Theo độ phức tạp: một văn bản/một chứng từ; nhiều tài liệu; nhiều bước; có ngoại lệ; có thay đổi hiệu lực.",
        "Theo trạng thái: đầy đủ; thiếu; unknown; notApplicable; mâu thuẫn; ngoài phạm vi.",
        "Theo kết quả kỳ vọng: có thể hỗ trợ kết luận; phải yêu cầu bổ sung; phải nêu mâu thuẫn; phải chuyển người.",
        "Theo khả năng hình thức hóa: đủ; chưa đủ do quy tắc mơ hồ; chưa đủ do dữ kiện không chắc chắn."
    ])
    doc.add_heading("3.3. Nhãn vàng bắt buộc", level=2)
    add_table(doc, ["Nhãn", "Nội dung"], [
        ("Nguồn", "Văn bản, phiên bản, điều/khoản và đoạn hỗ trợ; ngày áp dụng."),
        ("Bằng chứng", "Danh sách tài liệu/trường, vị trí, giá trị chuẩn hóa, liên kết và trạng thái."),
        ("Mâu thuẫn/thiếu", "Trường nào, giữa tài liệu nào, mức ảnh hưởng và hành động phù hợp."),
        ("Nhận định", "Các mệnh đề cần xuất hiện; mệnh đề không được khẳng định; mức chắc chắn."),
        ("Từ chối", "Có/không và lý do; yêu cầu bổ sung/chuyển người nào."),
        ("Lean", "Có đủ điều kiện không; rule version; giả thiết; kết luận; kết quả mong đợi; phản ví dụ nếu có."),
    ], widths=[4.0, 12.8])
    doc.add_paragraph(
        "Mỗi ca nên được hai người gắn nhãn độc lập; bất đồng được phân xử và lưu lý do. Tập giữ riêng "
        "được khóa bằng mã băm trước khi chạy đánh giá cuối để tránh thay đổi âm thầm."
    )

    doc.add_heading("4. TIÊU CHÍ VÀ CÁCH ĐO", level=1)
    doc.add_heading("4.1. Truy xuất và phiên bản", level=2)
    add_table(doc, ["Chỉ số", "Cách tính/diễn giải", "Áp dụng"], [
        ("Recall@k", "Tỷ lệ căn cứ vàng xuất hiện trong top-k; báo cáo theo ca và theo điều/khoản", "A/B/C"),
        ("MRR hoặc nDCG@k", "Đánh giá thứ hạng của căn cứ liên quan", "A/B/C"),
        ("Đúng phiên bản", "Tỷ lệ căn cứ đúng hiệu lực tại thời điểm ca", "A/B/C"),
        ("Độ chính xác trích dẫn", "Tỷ lệ trích dẫn thực sự hỗ trợ nhận định gắn với nó", "A/B/C"),
        ("Độ bao phủ trích dẫn", "Tỷ lệ nhận định trọng yếu có ít nhất một căn cứ hợp lệ", "A/B/C"),
    ], widths=[4.0, 8.3, 4.5])
    doc.add_heading("4.2. Hiểu hồ sơ và chuỗi bằng chứng", level=2)
    add_table(doc, ["Chỉ số", "Cách tính/diễn giải"], [
        ("F1 trích xuất trường", "Micro/macro precision, recall, F1 cho thực thể và giá trị chuẩn hóa."),
        ("Độ đúng liên kết", "Tỷ lệ cạnh đúng giữa hợp đồng–hóa đơn–tờ khai–vận tải–thanh toán."),
        ("F1 phát hiện thiếu", "So với danh sách thiếu vàng; tách absent và unknown."),
        ("F1 phát hiện mâu thuẫn", "Đúng trường, đúng cặp tài liệu và đúng loại mâu thuẫn."),
        ("Đúng notApplicable", "Chỉ chấp nhận khi có lý do/căn cứ; không tính unknown là notApplicable."),
    ], widths=[5.0, 11.8])
    doc.add_heading("4.3. Câu trả lời và hành vi từ chối", level=2)
    add_table(doc, ["Chỉ số", "Cách tính/diễn giải"], [
        ("Độ đúng nghiệp vụ", "Chấm theo rubric 0–2 cho từng nhận định; người chấm không biết cấu hình."),
        ("Bám nguồn", "Mệnh đề được suy ra từ đoạn được trích; không cộng điểm chỉ vì có citation."),
        ("Đầy đủ có kiểm soát", "Bao phủ điều kiện cần thiết nhưng không thêm khẳng định ngoài phạm vi."),
        ("Precision/recall từ chối", "Từ chối đúng khi thiếu/mâu thuẫn/ngoài phạm vi; tránh từ chối quá mức."),
        ("Selective accuracy và coverage", "Độ đúng trên các ca hệ thống dám trả lời, đi kèm tỷ lệ ca được trả lời."),
        ("Tính hữu dụng", "Rubric: rõ việc cần bổ sung, cấu trúc dễ kiểm tra, ngôn ngữ phù hợp người dùng."),
    ], widths=[5.0, 11.8])
    doc.add_heading("4.4. Kiểm chứng Lean", level=2)
    add_table(doc, ["Chỉ số", "Cách tính/diễn giải"], [
        ("Tỷ lệ ca đủ điều kiện", "Bao nhiêu ca thực sự có rule và dữ kiện đủ rõ để tạo nghĩa vụ chứng minh."),
        ("Đúng ánh xạ giả thiết", "Các giả thiết Lean khớp evidence ID/trạng thái; không tự điền missing/unknown."),
        ("Tỷ lệ nghĩa vụ hợp lệ", "Parse/typecheck/build thành công với theorem không đổi."),
        ("Đúng kết quả", "PASS/FAIL/UNKNOWN so với nhãn vàng và kiểm tra phản ví dụ."),
        ("Sai PASS nghiêm trọng", "Số ca PASS dù giả thiết/phiên bản/proof identity sai; mục tiêu bắt buộc là 0."),
        ("Nhất quán proof–answer", "Câu trả lời không diễn giải rộng hơn kết luận đã chứng minh."),
        ("Toàn vẹn proof", "Không sorry/admit; axiom trong allowlist; build sạch; khóa toolchain và dependency."),
    ], widths=[5.0, 11.8])
    doc.add_heading("4.5. Hiệu năng và vận hành", level=2)
    add_table(doc, ["Chỉ số", "Báo cáo"], [
        ("Độ trễ", "p50, p95 và tối đa; tách retrieval, agent loop, Lean, generation."),
        ("Chi phí", "Token vào/ra, số lần gọi model/công cụ, chi phí ước tính mỗi ca."),
        ("Ổn định", "Chạy lặp trên mẫu ca; tỷ lệ kết quả/trích dẫn thay đổi."),
        ("Khả năng phục hồi", "Timeout, lỗi OCR/retriever/Lean/model; fallback có giữ trạng thái an toàn không."),
        ("An toàn", "Tỷ lệ kịch bản prompt injection/phân quyền/phiên bản bị chặn đúng."),
    ], widths=[5.0, 11.8])

    doc.add_heading("5. QUY TRÌNH ĐÁNH GIÁ", level=1)
    add_numbered(doc, [
        "Khóa corpus snapshot, nguồn/phiên bản, bộ ca, nhãn vàng, cấu hình model, prompt, toolchain Lean và ngân sách.",
        "Hoàn thiện A trước; thêm điều phối để tạo B; thêm Lean trên nguyên trạng B để tạo C.",
        "Dùng tập phát triển để chọn top-k, ngưỡng, giới hạn bước và sửa lỗi; ghi toàn bộ quyết định.",
        "Đóng băng cấu hình. Mở tập giữ riêng một lần cho đánh giá chính thức; không tinh chỉnh lại theo kết quả giữ riêng.",
        "Chạy ba cấu hình trên cùng thứ tự ca và cùng điều kiện; lưu raw outputs, logs và artifact IDs.",
        "Chấm tự động các chỉ số xác định được; hai người chấm ẩn tên cấu hình cho tiêu chí nghiệp vụ/ngôn ngữ.",
        "Báo cáo trung bình, phân bố, khoảng tin cậy bootstrap; với kết quả nhị phân ghép cặp dùng kiểm định phù hợp như McNemar khi đủ cỡ mẫu.",
        "Phân tích lỗi theo nguồn, truy xuất, trích xuất, điều phối, hình thức hóa, proof, cổng đầu ra và sinh lời giải thích.",
        "Kết luận theo nhóm ca: Lean/Agentic RAG hữu ích ở đâu, gây chi phí ở đâu; không suy rộng ra ngoài mẫu/phạm vi."
    ])

    doc.add_heading("5.1. Mục tiêu kỹ thuật dự kiến", level=2)
    add_note(
        doc,
        "Lưu ý",
        "Các ngưỡng dưới đây là mục tiêu quản trị cho prototype, không phải kết quả đã đạt và không thay thế "
        "so sánh thống kê giữa ba cấu hình.",
        LIGHT_ORANGE,
    )
    add_table(doc, ["Hạng mục", "Mục tiêu dự kiến"], [
        ("Nguồn/phiên bản", "100% căn cứ phát hành có source ID, vị trí và phiên bản; 0 căn cứ sai hiệu lực trong tập giữ riêng."),
        ("Trích dẫn", "Độ chính xác ≥ 0,90; độ bao phủ nhận định trọng yếu ≥ 0,85."),
        ("Thiếu/mâu thuẫn", "F1 ≥ 0,80 trên tập giữ riêng, báo riêng theo loại."),
        ("Từ chối", "Không tối ưu accuracy đơn lẻ; đạt cân bằng precision/recall và công bố coverage."),
        ("Lean", "0 sai PASS nghiêm trọng; 100% proof phát hành vượt qua cổng toàn vẹn và identity."),
        ("An toàn", "100% kịch bản mức nghiêm trọng cao bị chặn hoặc chuyển người an toàn."),
        ("Tái lập", "100% lượt đánh giá có corpus/config/prompt/model/rule/toolchain IDs và log hoàn chỉnh."),
    ], widths=[5.0, 11.8])

    doc.add_heading("6. NỘI DUNG KHÔNG THỰC HIỆN", level=1)
    add_table(doc, ["Ngoài phạm vi", "Lý do/ranh giới"], [
        ("Tư vấn hoặc quyết định pháp lý tự động", "Hệ thống chỉ hỗ trợ; người có thẩm quyền phải duyệt."),
        ("Bao phủ toàn bộ pháp luật thuế", "Chỉ VAT đối với hoạt động xuất khẩu và nhóm hồ sơ đã xác định."),
        ("Pháp luật nước nhập khẩu", "Tài liệu nước ngoài chỉ là bằng chứng giao dịch, không phải corpus luật cần suy luận."),
        ("Xác thực chứng từ thật/giả", "Không có quyền truy cập hệ thống ngân hàng/hải quan để xác minh độc lập."),
        ("Tích hợp sản xuất với cơ quan thuế/hải quan/ngân hàng", "Prototype dùng file/mẫu và giao diện cục bộ; không gửi hồ sơ thật."),
        ("OCR mọi định dạng/chất lượng", "Chỉ hỗ trợ định dạng mục tiêu; ca OCR kém được gắn unknown/chuyển người."),
        ("Tự động hình thức hóa và kích hoạt luật không duyệt", "Mọi quy tắc Lean phải qua rà soát ngữ nghĩa và versioning."),
        ("Lean cho mọi câu hỏi", "Chỉ dùng khi quy tắc/dữ kiện đủ rõ; phần còn lại trả lời bám nguồn kèm giới hạn."),
        ("Chứng minh tính đầy đủ của corpus/truy xuất", "Lean không quan sát được tài liệu bị bỏ sót."),
        ("Bắt buộc multi-agent hoặc fine-tuning", "Chỉ là thí nghiệm tùy chọn sau khi hệ thống lõi và đánh giá ổn định."),
        ("Aristotle trong runtime sản phẩm", "Nếu có quyền truy cập, chỉ xem như đối chứng ngoài tùy chọn; không là phụ thuộc bắt buộc."),
        ("Cam kết loại bỏ hallucination", "Đo và giảm lỗi; không tuyên bố bảo đảm tuyệt đối."),
    ], widths=[6.0, 10.8])

    doc.add_heading("7. TIÊU CHÍ CHỐT/LOẠI THÀNH PHẦN", level=1)
    add_table(doc, ["Quyết định", "Giữ khi", "Loại/trì hoãn khi"], [
        ("Agentic loop", "Cải thiện thiếu/mâu thuẫn hoặc đúng nghiệp vụ đáng kể với chi phí chấp nhận", "Không tốt hơn A hoặc tăng lỗi/độ trễ không tương xứng"),
        ("Nhánh Lean", "Giảm kết luận không được hỗ trợ và tăng truy vết trên ca đủ điều kiện", "Formalization coverage quá thấp hoặc cổng identity không bảo đảm"),
        ("Multi-agent", "Ablation cho thấy tốt hơn single orchestrator trên cùng ngân sách", "Chỉ tăng độ phức tạp/không ổn định"),
        ("QLoRA/proof model", "Base model vs adapter trên held-out proof set cho lợi ích rõ và không tăng sai PASS", "Không vượt base hoặc không tái lập"),
        ("Aristotle", "Có quyền truy cập, chi phí chấp nhận và dùng như baseline độc lập", "Không sẵn có/không phù hợp yêu cầu dữ liệu"),
    ], widths=[3.7, 6.7, 6.4])

    doc.add_heading("8. SẢN PHẨM VÀ ĐIỀU KIỆN HOÀN THÀNH TUẦN 02", level=1)
    add_table(doc, ["Sản phẩm", "Điều kiện hoàn thành"], [
        ("Báo cáo lý thuyết và nghiệp vụ", "Bao phủ RAG, Agentic RAG, AI Agent, Lean 4; cấu trúc hồ sơ, chuỗi bằng chứng, yêu cầu chức năng/phi chức năng."),
        ("Sơ đồ kiến trúc và quy trình", "Tách offline/online; thể hiện nguồn luật, RAG, evidence store, orchestrator, Lean, output gate và audit."),
        ("Đặc tả phạm vi/đối chứng/đánh giá", "Chốt A/B/C, dữ liệu, chỉ số, quy trình, mục tiêu, nội dung không thực hiện và tiêu chí giữ/loại."),
    ], widths=[5.8, 11.0])

    doc.add_heading("TÀI LIỆU THAM CHIẾU CHÍNH", level=1)
    refs = [
        ("Lewis et al. – RAG", "https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html"),
        ("Karpukhin et al. – DPR", "https://aclanthology.org/2020.emnlp-main.550/"),
        ("Jeong et al. – Adaptive-RAG", "https://aclanthology.org/2024.naacl-long.389/"),
        ("Es et al. – RAGAS", "https://aclanthology.org/2024.eacl-demo.16/"),
        ("Gao et al. – ALCE/citation evaluation", "https://aclanthology.org/2023.emnlp-main.398/"),
        ("Lean Language Reference", "https://lean-lang.org/doc/reference/latest/"),
        ("Cổng TTĐT Chính phủ – Luật 48/2024/QH15", "https://vanban.chinhphu.vn/?classid=1&docid=212476&pageid=27160"),
        ("Cổng TTĐT Chính phủ – Nghị định 181/2025/NĐ-CP", "https://vanban.chinhphu.vn/?docid=214336&pageid=27160"),
        ("Cổng TTĐT Chính phủ – Thông tư 69/2025/TT-BTC", "https://vanban.chinhphu.vn/?classid=1&docid=214417&pageid=27160"),
    ]
    for label, url in refs:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.left_indent = Cm(0.6)
        add_hyperlink(p, label, url)

    doc.core_properties.title = "Đặc tả phạm vi, ba phương án đối chứng và kế hoạch đánh giá – Tuần 02"
    doc.core_properties.author = "Nguyễn Tuấn Minh"
    doc.core_properties.subject = "Thiết kế đánh giá RAG, Agentic RAG và Agentic RAG + Lean 4"
    doc.save(SPEC_PATH)


def validate_outputs() -> None:
    from zipfile import ZipFile
    for path in (REPORT_PATH, SPEC_PATH):
        # DOCX is a ZIP container; a text-heavy document can compress below
        # 50 KiB even when it contains all expected sections and tables.
        assert path.exists() and path.stat().st_size > 30_000, path
        with ZipFile(path) as zf:
            assert zf.testzip() is None, f"Corrupt DOCX: {path}"
            assert "word/document.xml" in zf.namelist()
    for path in (ARCH_V2_PNG, ARCH_V2_SVG):
        assert path.exists() and path.stat().st_size > 10_000, path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_architecture_v2_figure()
    build_report()
    build_spec()
    validate_outputs()
    for path in (REPORT_PATH, ARCH_V2_SVG, ARCH_V2_PNG, SPEC_PATH):
        print(f"{path.relative_to(ROOT)}\t{path.stat().st_size} bytes")


if __name__ == "__main__":
    main()

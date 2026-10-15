#!/usr/bin/env python3
"""Package only Week 4 output 1; do not claim the whole week is complete."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from build_corpus_release import ROOT, VERSION, export_release, verify_release

OUT = ROOT / "Nop_Bao_Cao_Tung_Tuan/Tuan_04"
RELEASE = ROOT / "data/corpus" / VERSION
STEM = "DA2_NguyenTuanMinh_Tuan4"


def table(doc, headers, rows):
    result = doc.add_table(rows=1, cols=len(headers))
    result.style = "Table Grid"
    for cell, value in zip(result.rows[0].cells, headers):
        cell.text = str(value)
        cell.paragraphs[0].runs[0].bold = True
    for row in rows:
        for cell, value in zip(result.add_row().cells, row):
            cell.text = str(value)
    return result


def build_report(summary, verification, pilot_summary=None):
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2), Cm(2)
    section.left_margin, section.right_margin = Cm(2.3), Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Times New Roman", Pt(11)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.1
    section.header.paragraphs[0].text = "ĐỒ ÁN 2 – NGUYỄN TUẤN MINH – TUẦN 04"
    section.header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.core_properties.author = "Nguyễn Tuấn Minh"
    doc.core_properties.title = f"Kho tài liệu pháp luật và nghiệp vụ {VERSION} – Tuần 04"
    doc.core_properties.subject = "Đầu ra 1 – snapshot nguồn, provenance và quản lý phiên bản"
    doc.add_paragraph("ĐẠI HỌC BÁCH KHOA HÀ NỘI", style="Subtitle")
    doc.add_heading(f"KHO TÀI LIỆU PHÁP LUẬT VÀ NGHIỆP VỤ {VERSION}", 0)
    doc.add_paragraph("Báo cáo đầu ra 1 – Tuần 04 – ngày 15/10/2026")
    table(doc, ["Thông tin", "Nội dung"], [
        ("Sinh viên / MSSV", "Nguyễn Tuấn Minh / 20237465"),
        ("Giảng viên hướng dẫn", "PGS.TS. Trần Ngọc Thăng"),
        ("Đề tài", "Agentic RAG hỗ trợ kiểm tra và hoàn thiện giải trình thuế GTGT đối với hoạt động xuất khẩu, tích hợp Lean 4"),
        ("Trạng thái", "Snapshot nghiên cứu v0.1 đã đóng gói; chưa phê duyệt làm căn cứ xử lý hồ sơ thực tế."),
    ])
    doc.add_heading("1. Mục tiêu và phạm vi", 1)
    doc.add_paragraph("Đóng băng kho tài liệu đã thu thập, giữ nguyên nguồn gốc và công khai chất lượng dữ liệu trước khi chia đoạn, lập chỉ mục và xây bộ ca đánh giá. Không tăng số lượng nguồn bằng cách coi mỗi điều, khoản hoặc mốc cấu trúc là một văn bản độc lập.")
    table(doc, ["Thành phần", "Kết quả thực tế"], [
        ("PDF pháp lý", f"{summary['legal_pdf_files']} tệp, {summary['pdf_pages']:,} trang PDF; chưa khẳng định tương ứng 37 văn bản đầy đủ."),
        ("Trích xuất chữ", f"{summary['text_extractable_sources']} nguồn có bản chữ; {summary['ocr_required_sources']} nguồn gần như toàn ảnh scan, chưa OCR."),
        ("Tài liệu nghiệp vụ", "2 tài liệu thiết kế nội bộ từ tuần 02; không phải hướng dẫn thuế chính thức hoặc hồ sơ doanh nghiệp."),
        ("Tài liệu nghiên cứu", "6 PDF nghiên cứu kỹ thuật được nhận diện riêng, không đưa vào kho căn cứ pháp lý."),
        ("Phê duyệt nghiệp vụ / hiệu lực", "Chưa hoàn tất. Ngày chưa xác minh để null; online_eligible=false."),
        ("Hồ sơ doanh nghiệp thực", "Chưa có trong release này."),
    ])
    doc.add_heading("2. Các bước đã thực hiện", 1)
    for text in [
        "Đối chiếu SHA-256 và số trang của từng PDF với kết quả kiểm kê ngày 14/10/2026; không sửa tệp PDF gốc.",
        "Trích xuất lại trực tiếp bằng pdftotext -layout, lưu UTF-8 JSONL theo trang PDF từ 1, giữ bản chữ và hash từng trang. Không dùng cache làm đầu vào bắt buộc.",
        "Tạo danh mục nguồn có ID, source version theo hash, tên/URL khai báo, nguồn metadata, nhóm phạm vi, trạng thái xử lý và cảnh báo chất lượng.",
        "Tên/URL được kế thừa từ Phụ lục A của danh mục tuần 01. Metadata này chưa được kiểm chứng lại trên website; không suy diễn hiệu lực từ ngày ban hành hoặc tên tệp.",
        "Tách 2 tài liệu nghiệp vụ nội bộ khỏi 37 PDF luật. Bản trích xuất tài liệu nội bộ giữ vị trí đoạn và hyperlink để truy vết.",
        "Đóng manifest, kiểm tra tính toàn vẹn và bàn giao trực tiếp bằng thư mục KhoTaiLieu, không tạo ZIP. Không ghi đè snapshot đã đóng băng hoặc thư mục bàn giao đã có chỉnh sửa khác.",
    ]:
        doc.add_paragraph(text, style="List Number")
    doc.add_heading("3. Chất lượng và hàng đợi rà soát", 1)
    table(doc, ["Nhóm nguồn", "Vấn đề / việc tiếp theo"], [
        ("03, 07, 13", "OCR và kiểm tra bản chữ. Chữ rất ít trích được không được coi là toàn văn."),
        ("20, 29, 30, 31, 33, 36, 37", "Bổ sung phần tiếp theo số Công báo; tệp 33 thiếu phần tiếp phụ lục."),
        ("14, 19, 33", "Xác định ranh giới từng văn bản trong PDF Công báo chứa nhiều văn bản."),
        ("32", "Chỉ có TT 21/2026 sửa TT 80/2021; tên tệp không đồng nghĩa đã có toàn văn TT 80/2021."),
        ("24–27", "Tài liệu quản trị AI/dữ liệu, tách khỏi căn cứ trả lời nghiệp vụ VAT."),
        ("Toàn bộ nguồn", "Review danh tính, phạm vi, tính đầy đủ, ngữ nghĩa và thời gian hiệu lực trước khi cho phép sử dụng online."),
    ])
    doc.add_paragraph("Không có cảnh báo ưu tiên không đồng nghĩa nguồn đầy đủ hoặc còn hiệu lực. Tổng quy tắc độc lập chưa xác định. Lean chỉ kiểm tra suy diễn của mã hóa; release này không phê duyệt quy tắc Lean hoặc chứng thực hồ sơ.")
    doc.add_heading("4. File và cách kiểm tra", 1)
    doc.add_paragraph("Bản v0.1.2 bàn giao bằng thư mục thay vì file nén; giữ ba file dữ liệu gọn, không thay đổi nội dung PDF/trích xuất và không nâng mức phê duyệt. Parent release ID giữ liên kết snapshot trước. Metadata và cảnh báo nằm trong manifest, không tạo CSV trùng dữ liệu.")
    doc.add_paragraph("Thư mục KhoTaiLieu/ có resources/ chứa PDF gốc; data/ chứa corpus; scripts/ và tests/ chứa mã nguồn/kiểm thử. DOCX tham chiếu giữ nguyên đường dẫn dưới Nop_Bao_Cao_Tung_Tuan/ để manifest vẫn truy vết được. Các đường dẫn trong bảng dưới tính từ KhoTaiLieu/.")
    table(doc, ["Đường dẫn", "Vai trò"], [
        (f"data/corpus/{VERSION}/manifest.json", "Danh mục luật/tài liệu nội bộ, thống kê, hash, phiên bản, metadata và cảnh báo/review; có kiểm kê đầu vào nhúng để tái lập."),
        (f"data/corpus/{VERSION}/pages.jsonl", "Toàn bộ chữ; kind phân biệt trang PDF luật với đoạn DOCX nội bộ. Mỗi dòng giữ ID/hash nguồn, hash chữ, vị trí trang/đoạn và hyperlink nếu có."),
        (f"data/corpus/{VERSION}/README.md", "Hướng dẫn chạy, chính sách dữ liệu và giới hạn. Đây là file hướng dẫn duy nhất trong corpus."),
        ("resources/references/*.pdf và DOCX gốc", "Tài liệu gốc giữ nguyên, đường dẫn nằm trong manifest; không tính vào ba file dữ liệu phát sinh."),
        ("scripts/build_corpus_release.py", "Tạo/kiểm tra/đóng gói release bằng Python standard library và pdftotext."),
    ])
    doc.add_paragraph("Mở terminal tại KhoTaiLieu/ và chạy; không cần giải nén:")
    for cmd in ["python3 scripts/build_corpus_release.py --verify-only",
                "python3 -m unittest discover -s tests -p 'test_corpus_release.py' -v"]:
        doc.add_paragraph(cmd)
    doc.add_paragraph(f"Kết quả kiểm tra: {verification['checked_artifacts']} artifact và {verification['checked_pdf_pages']:,} trang qua kiểm tra tính toàn vẹn. Đây là kiểm tra kỹ thuật, không phải xác nhận đúng pháp luật.")
    doc.add_heading("5. Phân biệt với hai đầu ra còn lại", 1)
    table(doc, ["Đầu ra tuần 04", "Trạng thái ở lần đóng gói này"], [
        ("1. Kho tài liệu v0.1", "Đã có snapshot/danh mục/bản trích xuất; bản gọn v0.1.2 bàn giao theo thư mục, không nâng mức độ phê duyệt."),
        ("2. Pipeline và index", "Có bước nạp/trích xuất, hash và quản lý phiên bản ở mức file. Chưa có chunking Điều–Khoản–Điểm hoặc keyword/semantic index; chưa triển khai PostgreSQL/pgvector."),
        ("3. Ca đánh giá và hướng dẫn gắn nhãn",
         (f"Đã có thư mục BoCaDanhGia: {pilot_summary['cases']} ca pilot giả lập, {pilot_summary['families']} họ tình huống; toàn bộ nhãn dự thảo, chưa được chuyên gia duyệt. Hướng dẫn ở BoCaDanhGia/README.md. Chưa có benchmark A/B/C."
          if pilot_summary else "Chưa được tạo trong gói này. Chưa có kết quả benchmark A/B/C.")),
    ])
    doc.add_paragraph(("Bước tiếp theo: hoàn thiện chia đoạn và chỉ mục; bổ sung hồ sơ độc lập và rà soát nhãn pilot trước benchmark. "
                       if pilot_summary else "Bước tiếp theo: xây bộ ca pilot và hướng dẫn gắn nhãn, sau đó hoàn thiện chia đoạn và chỉ mục. ")
                      + "Không cập nhật bảng tiến độ thành đã nộp chỉ vì đã tạo file.")
    return doc


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    integrity = verify_release(ROOT, RELEASE)
    test_command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_corpus_release.py", "-v"]
    result = subprocess.run(test_command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    manifest = json.loads((RELEASE / "manifest.json").read_text())
    summary = manifest["summary"]
    report_path = OUT / f"{STEM}_BaoCaoKhoTaiLieu_{VERSION}.docx"
    delivery_path = OUT / "KhoTaiLieu"
    export_release(ROOT, RELEASE, delivery_path)
    standalone_checks = []
    with tempfile.TemporaryDirectory(prefix="da2-week4-standalone-") as temp:
        shutil.copytree(delivery_path, temp, dirs_exist_ok=True)
        for command in ([sys.executable, "scripts/build_corpus_release.py", "--verify-only"],
                        test_command, [sys.executable, "scripts/build_corpus_release.py"]):
            check = subprocess.run(command, cwd=temp, capture_output=True, text=True)
            standalone_checks.append({"command": " ".join(command), "exit_code": check.returncode,
                                      "output": check.stdout + check.stderr})
            if check.returncode:
                raise RuntimeError("Standalone folder failed: " + check.stdout + check.stderr)
    tool = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=True)
    pilot_summary = None
    if (ROOT / "data/evaluation/pilot-v0.1/cases.jsonl").exists():
        from validate_pilot_cases import validate
        _, _, pilot_summary = validate(ROOT / "data/evaluation/pilot-v0.1", ROOT)
    report = build_report(summary, integrity, pilot_summary)
    report.add_heading("Phụ lục. Kiểm tra kỹ thuật", 1)
    report.add_paragraph("Gộp kết quả kiểm tra vào báo cáo, không phát sinh verification.json riêng. Nội dung này không phải review pháp lý/nghiệp vụ.")
    table(report, ["Mục", "Kết quả"], [
        ("Thời điểm kiểm tra UTC", datetime.now(timezone.utc).isoformat()),
        ("Release ID", manifest["release_id"]),
        ("Parent release ID", str(manifest["parent_release_id"])),
        ("Thư mục bàn giao", "KhoTaiLieu/; không tạo ZIP. Danh tính các nguồn và dữ liệu được khóa bằng release ID và hash trong manifest."),
        ("Toàn vẹn", f"{integrity['checked_artifacts']} artifact, {integrity['checked_pdf_pages']} trang PDF, {integrity['checked_business_paragraphs']} đoạn nội bộ; hash/locator hợp lệ."),
        ("Unit tests", (result.stdout + result.stderr).strip()),
        ("Thư mục độc lập", "Sao chép sang thư mục tạm mới; verify-only, unit tests và tái trích xuất đều exit 0, giữ nguyên release ID; không cần cache hoặc project gốc."),
        ("Toolchain", f"Python {sys.version}; {(tool.stdout + tool.stderr).strip()}"),
        ("Trạng thái", "Chưa có semantic/temporal approval; không thay đổi bảng tiến độ thành đã nộp."),
        ("Kiểm tra hiển thị", "DOCX được mở lại để kiểm tra nội dung và cấu trúc nội bộ; chưa render hình trang vì không có Office renderer."),
    ])
    with tempfile.TemporaryDirectory(prefix="da2-week4-report-") as temp:
        stage = Path(temp) / "report.docx"
        report.save(stage)
        with zipfile.ZipFile(stage) as archive:
            if archive.testzip():
                raise ValueError("Corrupt report DOCX")
        checked = Document(stage)
        text = "\n".join(p.text for p in checked.paragraphs)
        if "ĐẠI HỌC BÁCH KHOA HÀ NỘI" not in text or "TUẦN 03" in text:
            raise ValueError("Report identity mismatch")
        report_path.write_bytes(stage.read_bytes())
    print(json.dumps({"report": str(report_path), "delivery_directory": str(delivery_path), **integrity}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

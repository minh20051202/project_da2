#!/usr/bin/env python3
"""Read-only PDF extraction and structural inventory; not a semantic rule count.

The generated cache and CSV preserve source page/line references. Article hits
include quoted amendments until a reviewer marks the document/body boundaries.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".firecrawl" / "legal-corpus-inventory"
REPORT = ROOT / "docs" / "analysis" / "legal-corpus-inventory"
ARTICLE = re.compile(r'^\s*(?P<quote>[“"\u201c]?)\s*Điều\s+(?P<number>\d{1,3}[a-zđ]?)\s*[.:]\s*(?P<title>.+)$', re.I)
CLAUSE = re.compile(r'^\s*(?P<number>\d{1,3})\.\s+(?P<text>\S.*)$')
POINT = re.compile(r'^\s*(?P<number>[a-zđ](?:\d{1,2})?)\)\s+(?P<text>\S.*)$', re.I)
GROUPS = [(range(1, 11), "VAT core and amendments"),
          (range(11, 15), "Tax administration and electronic invoices"),
          (range(15, 19), "Customs"), (range(19, 20), "Bank payments"),
          (range(20, 24), "Penalties"), (range(24, 28), "Privacy and AI"),
          (range(28, 38), "Earlier sources and amendment chains")]
REVIEW_NOTES = {
    3: "Gần như toàn bộ là ảnh scan; chưa OCR/ngữ nghĩa.",
    7: "Gần như toàn bộ là ảnh scan; chưa OCR/ngữ nghĩa. Có bản hợp nhất liên quan ở tệp 06.",
    13: "838/839 trang ít chữ trích xuất; ảnh scan, nhiều biểu mẫu. Đã xem ảnh trang 2, chưa OCR toàn văn.",
    14: "Cả Công báo 402: NĐ 253/2026 nằm trước NĐ 254/2026; mục tiêu bắt đầu trang PDF 63.",
    19: "Cả Công báo 386: NĐ 236/2026 và VBHN 74 cùng với VBHN 75; mục tiêu bắt đầu trang PDF 70.",
    20: "Cuối tệp có chỉ dẫn Xem tiếp Công báo 1017 + 1018; kết thúc ở phần Điều 36.",
    29: "Chỉ phần đầu VBHN 21: đến Điều 4; cần phần tiếp Công báo 113 + 114.",
    30: "Chỉ một phần Luật 38/2019: kết thúc ở Điều 135; cần Công báo 563 + 564.",
    31: "Kết thúc ở Điều 30; cần phần tiếp Công báo 1021 + 1022.",
    32: "Nội dung là TT 21/2026 sửa TT 80/2021, không có toàn văn TT 80/2021 dù tên tệp ghi cả hai.",
    33: "Có NQ 1033/2020 trước NĐ 123/2020 (mục tiêu từ trang PDF 4); phần phụ lục có chỉ dẫn xem tiếp Công báo 1013 + 1014.",
    36: "Chỉ phần đầu TT 38/2015: đến Điều 53; cần Công báo 511 + 512.",
    37: "TT sửa đổi 39/2018 chưa đủ phần tiếp theo; cần Công báo 721 + 722.",
}


def group_for(n: int) -> str:
    return next(name for numbers, name in GROUPS if n in numbers)


def extract(pdf: Path) -> tuple[list[str], str, str]:
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    target = CACHE / f"{pdf.stem}-{sha[:12]}.txt"
    result = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                            capture_output=True, text=True, check=True)
    target.write_text(result.stdout, encoding="utf-8")
    pages = result.stdout.split("\f")
    if not pages[-1].strip():
        pages.pop()
    return pages, sha, result.stderr.strip()


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    documents, entries = [], []
    for pdf in sorted((ROOT / "resources/references").glob("*.pdf")):
        n = int(pdf.name[:2])
        if n > 37:
            continue
        pages, sha, warnings = extract(pdf)
        articles = []
        clause_hits = point_hits = 0
        for page_no, page in enumerate(pages, 1):
            for line_no, line in enumerate(page.splitlines(), 1):
                match = ARTICLE.match(line)
                if match:
                    article = {"source": pdf.name, "pdf_page": page_no,
                               "line": line_no, "kind": "article",
                               "label": match["number"], "quoted": bool(match["quote"]),
                               "text": match["title"].strip()}
                    articles.append(article)
                    entries.append(article)
                else:
                    match = CLAUSE.match(line)
                    kind = "clause"
                    if not match:
                        match = POINT.match(line)
                        kind = "point"
                    if match:
                        clause_hits += kind == "clause"
                        point_hits += kind == "point"
                        entries.append({"source": pdf.name, "pdf_page": page_no,
                                        "line": line_no, "kind": kind,
                                        "label": match["number"], "quoted": False,
                                        "text": match["text"].strip()})
        low_text = [i for i, p in enumerate(pages, 1)
                    if len(re.sub(r"\s+", "", p)) < 100]
        continuations = [{"pdf_page": i, "text": line.strip()}
                         for i, p in enumerate(pages, 1) for line in p.splitlines()
                         if re.search(r"xem\s+tiếp\s+công\s+báo", line, re.I)]
        item = {"source": pdf.name, "source_sha256": sha, "group": group_for(n),
                "pdf_pages": len(pages), "low_text_pages": len(low_text),
                "low_text_page_numbers": low_text,
                "article_heading_occurrences": len(articles),
                "unquoted_article_heading_occurrences": sum(not a["quoted"] for a in articles),
                "article_numbers_seen": sorted(set(a["label"] for a in articles)),
                "clause_marker_occurrences": clause_hits, "point_marker_occurrences": point_hits,
                "extraction_warnings": warnings, "articles": articles,
                "continuation_notices": continuations,
                "scan_dominated": len(low_text) / len(pages) > 0.9,
                "review_note": REVIEW_NOTES.get(n, "Chưa rà soát ngữ nghĩa/tính đầy đủ; không có cảnh báo ưu tiên từ phép kiểm tra này."),
                "status": "structural_extraction_only_not_semantic_review"}
        documents.append(item)
        print(f"{n:02d} pages={len(pages)} low_text={len(low_text)} "
              f"article_hits={len(articles)} clause_hits={clause_hits} point_hits={point_hits}")
    summary = {"documents": len(documents),
               "pdf_pages": sum(d["pdf_pages"] for d in documents),
               "low_text_pages": sum(d["low_text_pages"] for d in documents),
               "scan_dominated_sources": sum(d["scan_dominated"] for d in documents),
               "sources_with_continuation_notice": sum(bool(d["continuation_notices"]) for d in documents),
               "known_mixed_document_pdfs": 3,
               "raw_article_markers": sum(d["article_heading_occurrences"] for d in documents),
               "raw_clause_markers": sum(d["clause_marker_occurrences"] for d in documents),
               "raw_point_markers": sum(d["point_marker_occurrences"] for d in documents),
               "structural_markers": len(entries),
               "semantic_rule_total": None,
               "semantic_rule_total_status": "not_established_incomplete_and_unreviewed_corpus"}
    (REPORT / "source-audit.json").write_text(
        json.dumps({"count_definition": "Regex marker occurrences, NOT independent legal rules", "summary": summary,
                    "documents": documents}, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["source", "pdf_page", "line", "kind", "label", "quoted", "text"]
    with (REPORT / "structural-markers.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(entries)
    lines = ["# Kiểm kê 37 PDF pháp lý và khả năng đếm quy tắc", "",
             "Kiểm tra ngày 14/10/2026. Phạm vi: đúng 37 PDF có tiền tố 01–37 trong resources/references; 6 bài nghiên cứu không nằm trong phép đếm.", "",
             "## Kết quả", "",
             f"- {summary['documents']} tệp, {summary['pdf_pages']:,} trang PDF.",
             f"- {summary['scan_dominated_sources']} tệp gần như toàn ảnh scan (03, 07, 13); chưa OCR toàn văn.",
             f"- {summary['sources_with_continuation_notice']} tệp có chỉ dẫn xem tiếp số Công báo khác (20, 29, 30, 31, 33, 36, 37). Tệp 33 thiếu phần phụ lục; các tệp khác có phần nội dung chính tiếp ở số khác.",
             "- Ít nhất 3 PDF chứa văn bản ngoài tên tệp (14, 19, 33); cần chọn đúng phạm vi trang.",
             "- Tệp 32 chứa TT 21/2026 sửa TT 80/2021, chưa có toàn văn TT 80/2021.",
             "- **Chưa xác định được tổng quy tắc độc lập hoặc tổng quy tắc GTGT xuất khẩu.**", "",
             "## Những con số không được gọi là tổng quy tắc", "",
             f"Đếm máy thu được {summary['raw_article_markers']:,} lần xuất hiện tiêu đề Điều, {summary['raw_clause_markers']:,} mốc khoản dạng số và {summary['raw_point_markers']:,} mốc điểm dạng chữ, tổng {summary['structural_markers']:,} mốc. Chúng gồm cả cha và con, văn bản sửa đổi được trích lại, biểu mẫu, văn bản ngoài phạm vi tệp và các phiên bản trùng nội dung; ba PDF scan gần như không được tính. Đây không phải số quy tắc, không phải cận trên/cận dưới đáng tin cậy của số quy tắc.", "",
             "Một đơn vị quy tắc phục vụ formalization phải có nguồn chính xác, phạm vi/chủ thể, điều kiện, kết luận và ngoại lệ liên quan. Một khoản có thể tạo nhiều đơn vị; nhiều điểm có thể cùng tạo một đơn vị. Cần cố định quy ước tách trước khi đưa ra mẫu số.", "",
             "## Bảng nguồn", "",
             "Các mốc bên dưới là kết quả trích xuất cấu trúc, chưa loại trùng hay rà soát ngữ nghĩa. Không có cảnh báo không đồng nghĩa một tệp đã được xác nhận đầy đủ.", "",
             "| Tệp | Trang | Trang ít chữ | Mốc điều | Mốc khoản | Mốc điểm | Ghi chú kiểm tra |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for d in documents:
        lines.append(f"| {d['source']} | {d['pdf_pages']} | {d['low_text_pages']} | {d['article_heading_occurrences']} | {d['clause_marker_occurrences']} | {d['point_marker_occurrences']} | {d['review_note']} |")
    lines += ["", "## Bằng chứng và tái lập", "",
              "- source-audit.json: SHA-256 nguồn, số trang, vị trí tiêu đề và chỉ dẫn xem tiếp.",
              "- structural-markers.csv: toàn bộ mốc với tên PDF, trang PDF, dòng và đoạn đầu để rà soát.",
              "- .firecrawl/legal-corpus-inventory/: chữ trích xuất từ PDF gốc; không thay đổi PDF nguồn.",
              "- Tái lập: python3 scripts/audit_legal_corpus_inventory.py (pdftotext cần có trên máy).", "",
              "## Việc còn cần trước khi công bố tổng", "",
              "1. Thu thập đủ phần tiếp, bổ sung văn bản gốc còn thiếu, xác định đúng trang trong các PDF Công báo.",
              "2. OCR và kiểm tra chất lượng các tài liệu scan; phụ lục có quy định cần được xét riêng, không tự bỏ toàn bộ.",
              "3. Lập danh mục rule units có nguồn và phiên bản; phân loại quy tắc GTGT xuất khẩu, quy tắc hỗ trợ và nội dung ngoài scope.",
              "4. Đối chiếu bản gốc/sửa đổi/hợp nhất để nhóm quy tắc và giữ lịch sử phiên bản; chưa gộp chỉ vì câu chữ giống nhau.",
              "5. Rà soát ngữ nghĩa các đơn vị rồi mới tính tổng/độ phủ. Thống kê này không xác nhận hiệu lực pháp lý hiện tại.", ""]
    (REPORT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

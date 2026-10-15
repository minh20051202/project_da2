#!/usr/bin/env python3
"""Freeze an auditable source corpus, not an approved legal knowledge base.

Uses existing local sources only. Does not fetch documents, OCR scans, infer
effective dates, approve rules, change PDFs, or update submission status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v0.1.2"
AUDIT = Path("docs/analysis/legal-corpus-inventory/source-audit.json")
REFERENCES = Path("Nop_Bao_Cao_Tung_Tuan/Tuan_01/DA2_NguyenTuanMinh_Tuan1_TaiLieuThamKhao.docx")
BUSINESS = (
    Path("Nop_Bao_Cao_Tung_Tuan/Tuan_02/DA2_NguyenTuanMinh_Tuan2_BaoCaoTongQuanLyThuyet_YeuCauNghiepVu.docx"),
    Path("Nop_Bao_Cao_Tung_Tuan/Tuan_02/DA2_NguyenTuanMinh_Tuan2_DacTaPhamVi_DoiChung_DanhGia.docx"),
)
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode()


def read_docx_paragraphs(path: Path) -> list[dict]:
    """Read body/table paragraph text and hyperlink targets without executing content."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
        relationships = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        links = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
    rows = []
    for number, paragraph in enumerate(root.findall(".//w:p", NS), 1):
        text = "".join(t.text or "" for t in paragraph.findall(".//w:t", NS))
        urls = [links[link.attrib[f"{{{NS['r']}}}id"]]
                for link in paragraph.findall(".//w:hyperlink", NS)
                if f"{{{NS['r']}}}id" in link.attrib]
        rows.append({"paragraph": number, "text": text, "urls": urls})
    return rows


def read_reference_metadata(path: Path) -> dict[int, dict]:
    """Import declarations from Week 1; do NOT promote them to verified law metadata."""
    rows = read_docx_paragraphs(path)
    heading = "Phụ lục A. Danh mục tài liệu tham khảo đầy đủ"
    positions = [index for index, row in enumerate(rows) if row["text"] == heading]
    if not positions:
        raise ValueError("Missing Appendix A reference catalog")
    # The narrative groups several laws in a single numbered item. Appendix A
    # has the 1:1 PDF acquisition ordering; its numbering is Word list metadata.
    references = [row for row in rows[positions[-1] + 1:] if row["urls"]]
    if len(references) < 37:
        raise ValueError("Appendix A contains fewer than 37 source entries")
    metadata = {}
    for number, row in enumerate(references[:37], 1):
        urls = [url for url in row["urls"] if url.startswith(("https://", "http://"))]
        if len(urls) != 1:
            raise ValueError(f"Ambiguous source URL at reference {number}")
        metadata[number] = {"declared_title": row["text"].removesuffix(" Nguồn"),
                            "declared_source_url": urls[0],
                            "reference_heading_paragraph": row["paragraph"],
                            "reported_metadata_text": row["text"]}
    return metadata


def split_pdf_pages(text: str) -> list[str]:
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def classify_scope(number: int) -> str:
    if number <= 10:
        return "vat_core_and_amendments"
    if number <= 23:
        return "supporting_procedure_customs_payment_penalties"
    if number <= 27:
        return "system_governance_not_vat_answer_authority"
    return "earlier_sources_and_amendment_chains"


def quality_issues(item: dict, number: int) -> list[str]:
    issues = ["semantic_review_pending", "temporal_review_pending"]
    if item["scan_dominated"]:
        issues.append("ocr_required")
    if item["low_text_pages"] and not item["scan_dominated"]:
        issues.append("some_pages_have_little_extracted_text")
    if item["continuation_notices"]:
        issues.append("continuation_in_another_gazette_issue")
    if number in (14, 19, 33):
        issues.append("multiple_legal_documents_in_pdf_boundaries_need_review")
    if number == 32:
        issues.append("filename_mismatch_only_amending_circular_present")
    return issues


def file_record(path: str, content: bytes, role: str) -> dict:
    return {"path": path, "sha256": sha256(content), "bytes": len(content), "role": role}


def corpus_readme(version: str, summary: dict) -> bytes:
    return f"""# Kho tài liệu {version} — đầu ra 1, tuần 04

Bản đóng gói gọn ngày 15/10/2026, kế thừa snapshot v0.1. Không thay đổi nguồn
luật hoặc nâng trạng thái phê duyệt. Phiên bản chính xác và parent release ID
được lưu trong manifest.json.

## Chỉ ba file dữ liệu

- `manifest.json`: danh mục nguồn, hash/phiên bản, thống kê, metadata kế thừa,
  cảnh báo và trạng thái review. Không cần CSV hoặc JSON riêng cho từng bảng.
- `pages.jsonl`: toàn bộ chữ trích xuất. Mỗi dòng có `kind`, `source_id`,
  `source_version_id`, `source_sha256`, `text`, `text_sha256` cùng locator.
- `README.md`: hướng dẫn này.

PDF/DOCX gốc vẫn được lưu riêng theo `artifact_path` trong manifest, không bị
chỉnh sửa. Các đường dẫn tính từ thư mục bàn giao `KhoTaiLieu/`.

## Phạm vi và cách đọc

{summary['legal_pdf_files']} PDF pháp lý, {summary['pdf_pages']:,} trang PDF;
{summary['internal_business_documents']} tài liệu thiết kế nghiệp vụ nội bộ từ
tuần 02, không phải hướng dẫn thuế chính thức hoặc hồ sơ doanh nghiệp thực.
6 PDF nghiên cứu kỹ thuật được liệt kê riêng, không đưa vào căn cứ pháp lý.

Metadata pháp lý nằm trong `sources`; tài liệu nội bộ trong `business_sources`;
thống kê trong `summary`. Cảnh báo và việc cần duyệt nằm ngay trong từng source:
`quality_issues`, `review_note`, `review`. Kiểm kê cần cho tái lập đã nhúng trong
`inventory_snapshot`, không cần phát sinh thêm file audit trong gói nộp.

`kind=legal_pdf_page` có `pdf_page` bắt đầu từ 1. `text` giữ nguyên chữ do
pdftotext -layout trích xuất, bao gồm xuống dòng/khoảng trắng. Chưa phải bản chữ
được người duyệt; không bảo đảm công cụ trích xuất đúng mọi ký tự/bảng biểu.
`kind=internal_business_paragraph` có `paragraph` bắt đầu từ 1 và `urls` lấy từ
DOCX gốc. Chỉ dùng kind pháp lý khi xây legal index; không trộn tài liệu nội bộ
thành căn cứ luật chỉ vì nằm cùng một file vật lý.

Tên văn bản/URL kế thừa Phụ lục A tuần 01, có hash/locator tham chiếu nhưng chưa
được đối chiếu lại website. Metadata khai báo cũ giữ trong `reported_metadata_text`.
Ngày tải/hiệu lực chưa xác minh để null, không suy đoán từ tên tệp/ngày ban hành.
`source_id` là ID nội bộ, không thay số hiệu văn bản. Source version dùng SHA-256
đầy đủ; một PDF Công báo có thể chứa nhiều văn bản.

## Giới hạn giữ nguyên

- 03, 07, 13 cần OCR; {summary['text_extractable_sources']} nguồn có chữ không
  đồng nghĩa đã được duyệt đầy đủ hoặc đúng hiệu lực.
- 20, 29, 30, 31, 33, 36, 37 có chỉ dẫn phần tiếp; tệp 33 thiếu phần phụ lục tiếp.
- 14, 19, 33 chứa nhiều văn bản, cần rà ranh giới; tệp 32 chỉ có TT 21/2026 sửa
  TT 80/2021 chứ chưa có toàn văn TT 80/2021.
- 24–27 là quản trị AI/dữ liệu, không phải căn cứ trả lời nghiệp vụ VAT.
- Tất cả nguồn còn pending semantic/temporal review, `online_eligible=false`.
  Không có cảnh báo ưu tiên không có nghĩa là nguồn đầy đủ hoặc còn hiệu lực.
- Chưa có hồ sơ doanh nghiệp thực; chưa xác định tổng quy tắc độc lập.

## Chạy và kiểm tra

Từ project root hoặc thư mục bàn giao `KhoTaiLieu/` (Python 3.10+):

```bash
python3 scripts/build_corpus_release.py --verify-only
python3 -m unittest discover -s tests -p 'test_corpus_release.py' -v
```

Tái trích xuất cần thêm Poppler/pdftotext; không cần mạng, API key hay PostgreSQL:

```bash
python3 scripts/build_corpus_release.py
```

Cùng dữ liệu chạy lại không đổi release. Kết quả khác bản đóng băng thì dừng,
không ghi đè; cần review và tạo version mới. Hash kiểm tra tính toàn vẹn, không
chứng minh tính xác thực pháp lý hoặc phê duyệt nội dung. Gói có thể tái lập mà
không phụ thuộc `.firecrawl` hoặc file kiểm kê bên ngoài thư mục bàn giao.

Bàn giao trực tiếp bằng các thư mục, không tạo file nén:

```bash
python3 scripts/build_corpus_release.py --verify-only --export-dir Nop_Bao_Cao_Tung_Tuan/Tuan_04/KhoTaiLieu
```

Thư mục bàn giao có `resources/` (PDF gốc), `data/` (ba file corpus),
`scripts/` và `tests/` (mã nguồn/kiểm thử). Các DOCX tham chiếu được giữ dưới
đường dẫn gốc `Nop_Bao_Cao_Tung_Tuan/` để hash và liên kết trong manifest vẫn đúng.

## Trạng thái tuần 04

Đã có đầu ra 1 ở mức snapshot v0.1 có giới hạn, được đóng gói gọn thành {version}.
Đầu ra 2 mới có nạp/trích xuất/quản lý phiên bản mức file; chưa có chunking
Điều–Khoản–Điểm, chỉ mục từ khóa/ngữ nghĩa hoặc PostgreSQL/pgvector.
Đầu ra 3 (ca đánh giá và hướng dẫn gắn nhãn) chưa tạo. Chưa chạy benchmark A/B/C,
chưa tự cập nhật bảng tiến độ thành đã nộp hoặc phê duyệt Lean packet.
""".encode()


def build_payload(root: Path, version: str, extractor=None, parent_release_id=None) -> tuple[dict[str, bytes], dict, list[dict]]:
    if not re.fullmatch(r"v\d+\.\d+(?:\.\d+)?", version):
        raise ValueError("Version must look like v0.1 or v0.1.1")
    previous_path = root / "data/corpus" / version / "manifest.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    if parent_release_id is None:
        parent_release_id = previous.get("parent_release_id")
    if (root / AUDIT).exists():
        audit = json.loads((root / AUDIT).read_text())
        inventory_provenance = file_record(AUDIT.as_posix(), (root / AUDIT).read_bytes(), "prior_structural_inventory")
    elif "inventory_snapshot" in previous:
        audit = previous["inventory_snapshot"]
        inventory_provenance = previous["inventory_provenance"]
    else:
        raise ValueError("Missing prior inventory and no embedded inventory in this release")
    fields = ("source", "source_sha256", "group", "pdf_pages", "low_text_pages",
              "low_text_page_numbers", "continuation_notices", "scan_dominated", "review_note")
    inventory = {"summary": audit["summary"],
                 "documents": [{key: item[key] for key in fields} for item in audit["documents"]]}
    audited = {item["source"]: item for item in audit["documents"]}
    metadata = read_reference_metadata(root / REFERENCES)
    candidates = sorted((root / "resources/references").glob("*.pdf"))
    pdfs = [p for p in candidates if p.name[:2].isdigit() and 1 <= int(p.name[:2]) <= 37]
    if len(pdfs) != 37 or set(p.name for p in pdfs) != set(audited):
        raise ValueError("Expected exactly the 37 audited legal source PDFs")
    payload: dict[str, bytes] = {}
    originals = []
    sources = []
    records = []
    if extractor is None:
        def extractor(path):
            result = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                                    capture_output=True, encoding="utf-8", check=True)
            return result.stdout, result.stderr.strip()
    for path in pdfs:
        raw = path.read_bytes()
        number = int(path.name[:2])
        item = audited[path.name]
        digest = sha256(raw)
        if digest != item["source_sha256"]:
            raise ValueError(f"Source changed since inventory: {path.name}; re-audit before release")
        text, warnings = extractor(path)
        pages = split_pdf_pages(text)
        if len(pages) != item["pdf_pages"]:
            raise ValueError(f"PDF page-count mismatch: {path.name}")
        source_id = f"LEGAL-{number:03d}"
        source_version_id = f"{source_id}@sha256:{digest}"
        page_rows = [{"kind": "legal_pdf_page", "source_id": source_id, "source_version_id": source_version_id,
                      "source_sha256": digest, "pdf_page": page_number,
                      "text": page, "text_sha256": sha256(page.encode()),
                      "extraction": "pdftotext-layout", "ocr_applied": False,
                      "low_text": len(re.sub(r"\s+", "", page)) < 100}
                     for page_number, page in enumerate(pages, 1)]
        records.extend(page_rows)
        issues = quality_issues(item, number)
        source = {
            "source_id": source_id, "source_version_id": source_version_id,
            "artifact_path": path.relative_to(root).as_posix(),
            "source_sha256": digest, "bytes": len(raw), "pdf_pages": len(pages),
            "kind": "legal_source_candidate", "scope_group": classify_scope(number),
            "inventory_group": item["group"], **metadata[number],
            "metadata_provenance": {"path": REFERENCES.as_posix(),
                                    "sha256": sha256((root / REFERENCES).read_bytes()),
                                    "status": "prior_report_declarations_not_reverified"},
            "downloaded_at": None, "effective_from": None, "effective_to": None,
            "temporal_review": "pending", "semantic_review": "pending",
            "approval": "not_approved", "online_eligible": False,
            "coverage_status": "not_verified_complete",
            "processing_status": "ocr_required" if item["scan_dominated"] else "text_extracted_unreviewed",
            "offline_text_available": not item["scan_dominated"],
            "extracted_pages_path": "pages.jsonl",
            "low_text_page_numbers": item["low_text_page_numbers"],
            "quality_issues": issues, "review_note": item["review_note"],
            "extraction_warnings": warnings,
            "continuation_notices": item["continuation_notices"],
            "document_boundary_review": "pending",
            "review": {"blocking_online_use": True, "reviewer": None, "resolution": None},
        }
        sources.append(source)
        originals.append(file_record(source["artifact_path"], raw, "original_legal_pdf"))

    business = []
    for number, rel in enumerate(BUSINESS, 1):
        raw = (root / rel).read_bytes()
        digest = sha256(raw)
        rows = read_docx_paragraphs(root / rel)
        source_id = f"BUS-{number:03d}"
        source_version_id = f"{source_id}@sha256:{digest}"
        records.extend({**row, "kind": "internal_business_paragraph", "source_id": source_id,
                        "source_version_id": source_version_id, "source_sha256": digest,
                        "text_sha256": sha256(row["text"].encode())} for row in rows)
        business.append({"source_id": source_id, "source_version_id": source_version_id, "artifact_path": rel.as_posix(),
                         "sha256": digest, "kind": "internal_project_business_design",
                         "authority": "not_a_legal_authority", "review_status": "not_expert_validated",
                         "real_enterprise_dossier": False, "online_legal_index_eligible": False,
                         "paragraph_count": len(rows), "extracted_paragraphs_path": "pages.jsonl"})
        originals.append(file_record(rel.as_posix(), raw, "internal_business_design_docx"))
    payload["pages.jsonl"] = jsonl_bytes(records)
    summary = {
        "legal_pdf_files": len(sources), "pdf_pages": sum(s["pdf_pages"] for s in sources),
        "text_extractable_sources": sum(s["offline_text_available"] for s in sources),
        "ocr_required_sources": sum(s["processing_status"] == "ocr_required" for s in sources),
        "sources_with_continuation_notice": sum(bool(s["continuation_notices"]) for s in sources),
        "known_mixed_document_pdfs": sum("multiple_legal_documents_in_pdf_boundaries_need_review" in s["quality_issues"] for s in sources),
        "internal_business_documents": len(business), "real_enterprise_dossiers": 0,
        "internal_business_paragraphs": sum(s["paragraph_count"] for s in business),
        "approved_legal_sources": 0, "approved_rules_added": 0,
        "research_pdfs_excluded": ([p.name for p in candidates if p not in pdfs]
                                   or previous.get("summary", {}).get("research_pdfs_excluded", [])),
        "independent_legal_rules_total": None,
        "note": "File/page counts are not counts of provisions, rules, or VAT-export coverage.",
    }
    payload["README.md"] = corpus_readme(version, summary)
    originals.append(file_record(REFERENCES.as_posix(), (root / REFERENCES).read_bytes(), "metadata_reference_report"))
    manifest = {
        "schema_version": "da2-source-corpus/2", "release_version": version,
        "release_date": "2026-10-15", "status": "source_snapshot_not_approved_knowledge_base",
        "parent_release_id": parent_release_id,
        "change_note": "Compact physical layout; source PDFs and extracted text unchanged from v0.1.",
        "identity_policy": "source_version_id uses the full PDF SHA-256; release identity hashes the manifest without release_id",
        "effective_time_policy": "Unknown dates stay null; no current-law or historical applicability inferred from filenames or report dates.",
        "citation_policy": "PDF page is 1-based; text is raw pdftotext -layout output, not expert-validated OCR or original legal bytes.",
        "normalization_policy": "Stable UTF-8 JSON/JSONL, explicit nulls, categorized sources and hashes; no legal-text rewriting.",
        "release_path": f"data/corpus/{version}", "summary": summary,
        "sources": sources, "business_sources": business,
        "inventory_provenance": inventory_provenance, "inventory_snapshot": inventory,
        "original_artifacts": sorted(originals, key=lambda x: x["path"]),
        "derived_artifacts": [file_record(path, raw, "derived_corpus_artifact")
                              for path, raw in sorted(payload.items())],
        "pending_deliverables": ["article_clause_point_chunking", "keyword_and_semantic_index",
                                 "initial_evaluation_cases_and_labeling_guide"],
    }
    manifest["release_id"] = f"corpus-{version}-sha256:{sha256(json_bytes(manifest))}"
    payload["manifest.json"] = json_bytes(manifest)
    return payload, manifest, sources


def freeze_release(destination: Path, payload: dict[str, bytes]) -> None:
    """Immutable release: refuse to change or silently overwrite an existing version."""
    if destination.exists():
        existing = {p.relative_to(destination).as_posix(): p.read_bytes()
                    for p in destination.rglob("*") if p.is_file()}
        if existing != payload:
            raise ValueError(f"{destination} already exists with different content; create a new version")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="da2-corpus-", dir=destination.parent) as temp:
        stage = Path(temp) / "release"
        stage.mkdir()
        for name, content in payload.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        stage.rename(destination)


def verify_release(root: Path, release: Path) -> dict:
    manifest = json.loads((release / "manifest.json").read_text())
    identity = manifest.pop("release_id")
    expected = f"corpus-{manifest['release_version']}-sha256:{sha256(json_bytes(manifest))}"
    if identity != expected:
        raise ValueError("Manifest identity mismatch")
    if manifest.get("schema_version") != "da2-source-corpus/2":
        raise ValueError("This verifier expects the compact corpus schema /2")
    if {p.relative_to(release).as_posix() for p in release.rglob("*") if p.is_file()} != {"manifest.json", "pages.jsonl", "README.md"}:
        raise ValueError("Compact release must contain exactly three files")
    checked = 0
    for record in manifest["original_artifacts"] + manifest["derived_artifacts"]:
        base = root if record in manifest["original_artifacts"] else release
        path = base / record["path"]
        raw = path.read_bytes()
        if sha256(raw) != record["sha256"] or len(raw) != record["bytes"]:
            raise ValueError(f"Artifact mismatch: {path}")
        checked += 1
    sources = manifest["sources"]
    business = manifest["business_sources"]
    grouped = {s["source_id"]: [] for s in sources + business}
    if len(grouped) != len(sources) + len(business):
        raise ValueError("Duplicate source ID")
    for line in (release / "pages.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["source_id"] not in grouped:
            raise ValueError("Unknown record source ID")
        grouped[row["source_id"]].append(row)
    originals = {record["path"]: record for record in manifest["original_artifacts"]}
    for source in sources + business:
        pages = grouped[source["source_id"]]
        is_legal = source["source_id"].startswith("LEGAL-")
        digest = source["source_sha256"] if is_legal else source["sha256"]
        if source["source_version_id"] != f"{source['source_id']}@sha256:{digest}" or originals[source["artifact_path"]]["sha256"] != digest:
            raise ValueError("Source version identity mismatch")
        locator = "pdf_page" if is_legal else "paragraph"
        count = source["pdf_pages"] if is_legal else source["paragraph_count"]
        if [p[locator] for p in pages] != list(range(1, count + 1)):
            raise ValueError(f"Record sequence mismatch: {source['source_id']}")
        kind = "legal_pdf_page" if is_legal else "internal_business_paragraph"
        for page in pages:
            if (page["kind"] != kind or page["source_sha256"] != digest
                    or page["source_version_id"] != source["source_version_id"]
                    or sha256(page["text"].encode()) != page["text_sha256"]):
                raise ValueError("Record provenance mismatch")
        if is_legal and (source["online_eligible"] or source["effective_from"] is not None or source["effective_to"] is not None):
            raise ValueError("Unreviewed source was silently promoted")
        if not is_legal and (source["online_legal_index_eligible"] or source["real_enterprise_dossier"]):
            raise ValueError("Internal document was silently promoted")
    return {"status": "technical_integrity_checks_passed", "release_id": identity,
            "checked_artifacts": checked, "checked_pdf_pages": sum(s["pdf_pages"] for s in sources),
            "checked_business_paragraphs": sum(s["paragraph_count"] for s in business),
            "legal_approval": "not_approved", "submission_status_changed": False}


def export_release(root: Path, release: Path, target: Path) -> None:
    """Copy a self-contained folder; never archive it or overwrite local edits."""
    target = target.resolve()
    if root.resolve().is_relative_to(target) or target.is_relative_to(release.resolve()):
        raise ValueError("Export target must not replace a workspace or corpus release")
    verify_release(root, release)
    manifest = json.loads((release / "manifest.json").read_text())
    paths = {root / item["path"] for item in manifest["original_artifacts"]}
    paths.update(p for p in release.rglob("*") if p.is_file())
    paths.update(root / p for p in ("scripts/build_corpus_release.py", "tests/test_corpus_release.py"))
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = {path.relative_to(root).as_posix(): path for path in paths}
    if target.exists():
        existing = {p.relative_to(target).as_posix(): p for p in target.rglob("*") if p.is_file()}
        if set(existing) != set(expected) or any(
                sha256(existing[name].read_bytes()) != sha256(path.read_bytes())
                for name, path in expected.items()):
            raise ValueError("Export directory already exists with different content; preserve it before exporting again")
        return
    with tempfile.TemporaryDirectory(prefix="da2-corpus-export-", dir=target.parent) as temp:
        stage = Path(temp) / "delivery"
        stage.mkdir()
        for name, path in sorted(expected.items()):
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        verify_release(stage, stage / release.relative_to(root))
        stage.rename(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--parent-release-id", help="Previous immutable release identity")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--export-dir", type=Path, help="Self-contained submission directory (no archive)")
    args = parser.parse_args()
    if not re.fullmatch(r"v\d+\.\d+(?:\.\d+)?", args.version):
        parser.error("Invalid version")
    release = ROOT / "data/corpus" / args.version
    if not args.verify_only:
        payload, _, _ = build_payload(ROOT, args.version, parent_release_id=args.parent_release_id)
        freeze_release(release, payload)
    result = verify_release(ROOT, release)
    if args.export_dir:
        export_release(ROOT, release, args.export_dir)
        result["export_directory"] = str(args.export_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

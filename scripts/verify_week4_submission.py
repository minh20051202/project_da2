#!/usr/bin/env python3
"""Run reproducible Week-4 technical checks; never submit or grant legal approval."""
import argparse
import collections
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from build_corpus_release import ROOT, verify_release
from legal_retrieval import CORPUS, E5, load_index, search, structural_chunks
from validate_pilot_cases import DATASET, check_lean, validate


def verify(with_lean=False):
    started = time.monotonic()
    corpus_result = verify_release(ROOT, CORPUS)
    _, labels, pilot_result = validate(DATASET, ROOT)
    chunks, vectors, manifest = load_index()
    corpus = json.loads((CORPUS / "manifest.json").read_text())
    pages = collections.defaultdict(list)
    for line in (CORPUS / "pages.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["kind"] == "legal_pdf_page":
            pages[row["source_id"]].append(row)
    rebuilt = []
    for source in corpus["sources"]:
        if source["source_id"] in manifest["selected_source_versions"]:
            rebuilt.extend(structural_chunks(source, pages[source["source_id"]]))
    if rebuilt != chunks:
        raise ValueError("Regenerated structural spans differ from the frozen index")
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    unit = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    if unit.returncode:
        raise RuntimeError(unit.stdout + unit.stderr)
    count = re.search(r"Ran (\d+) tests?", unit.stderr)
    if not count:
        raise ValueError("No tests executed")
    encoder = E5()
    probes = [
        ("input_invoice", "hóa đơn giá trị gia tăng mua hàng hóa dịch vụ hoặc chứng từ nộp thuế ở khâu nhập khẩu", "a"),
        ("purchase_payment", "chứng từ thanh toán không dùng tiền mặt đối với hàng hóa dịch vụ mua vào điều kiện khấu trừ", "b"),
        ("export_documents", "hợp đồng với bên nước ngoài tờ khai hải quan phiếu đóng gói vận đơn chứng từ bảo hiểm xuất khẩu", "c"),
    ]
    smoke = []
    for query_id, query, point in probes:
        for mode in ("keyword", "semantic", "hybrid"):
            before = time.monotonic()
            output = search(query, chunks, vectors, manifest, ["LEGAL-001"], mode, offline=True, encoder=encoder)
            if not output["results"] or any(row["source_id"] != "LEGAL-001" for row in output["results"]):
                raise ValueError("Retrieval failed or crossed the explicit source-version filter")
            hit = any(row["article"] == "14" and row["clause"] == "2" and row["point"] == point for row in output["results"])
            smoke.append({"query_id": query_id, "query": query, "mode": mode,
                          "expected_anchor": {"article": "14", "clause": "2", "point": point},
                          "anchor_in_top5": hit, "sample_elapsed_seconds": round(time.monotonic() - before, 4),
                          "top5": [{k: row[k] for k in ("chunk_id", "source_id", "article", "clause", "point", "pdf_page_start", "pdf_page_end")} for row in output["results"]]})
    online = search("hoàn thuế", chunks, vectors, manifest, ["LEGAL-001"], as_of="2026-10-15", encoder=encoder)
    if online["status"] != "no_eligible_sources":
        raise ValueError("Candidate source must not be online-eligible")
    result = {
        "status": "technical_checks_passed_not_legal_approval", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "corpus": corpus_result, "pilot": pilot_result,
        "retrieval": {"index_id": manifest["index_id"], "selected_sources": list(manifest["selected_source_versions"]),
                      "chunks": len(chunks), "pdf_pages": manifest["pdf_pages"], "embedding_dimension": manifest["dimension"],
                      "model_id": manifest["model"]["id"], "model_revision": manifest["model"]["revision"],
                      "truncated_embedding_inputs": manifest["truncated_embedding_inputs"],
                      "raw_citation_spans_regenerated": True, "online_candidate_gate": "blocked_as_expected",
                      "smoke_searches": smoke, "anchor_hits_top5": sum(row["anchor_in_top5"] for row in smoke),
                      "smoke_note": "Three known source anchors x three retrievers; not held-out quality, independent cases, or A/B/C benchmark."},
        "unit_tests": {"command": " ".join(command), "exit_code": 0, "count": int(count[1]), "output": unit.stderr.strip()},
        "lean": {"status": "not_run_add_--with-lean_to_check"},
        "limits": {"abc_benchmark_run": False, "expert_labels_approved": 0, "production_pgvector_deployed": False,
                   "all_37_sources_indexed": False, "ocr_completed": False, "legal_approval": False,
                   "weekly_submission_status_changed": False},
    }
    if with_lean:
        result["lean"] = check_lean(labels, ROOT)
        packet = subprocess.run([sys.executable, "-B", "scripts/verify_article14_packet.py"],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        if packet.returncode:
            raise RuntimeError(packet.stdout + packet.stderr)
        result["seed_packet"] = json.loads(packet.stdout)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-lean", action="store_true")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    result = verify(args.with_lean)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(encoded + "\n")
        print(json.dumps({"status": result["status"], "output": str(args.output_json),
                          "tests": result["unit_tests"]["count"], "chunks": result["retrieval"]["chunks"],
                          "smoke_anchor_hits": result["retrieval"]["anchor_hits_top5"]}, ensure_ascii=False))
    else:
        print(encoded)


if __name__ == "__main__":
    main()

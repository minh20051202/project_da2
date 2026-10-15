#!/usr/bin/env python3
"""Validate synthetic pilot inputs/draft labels; optionally check offline Lean fixtures.

This is not an A/B/C evaluator, evidence extractor, or legal approval tool.
Only cases.jsonl is model input. labels.jsonl is restricted to scorer/review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/pilot-v0.1"
if not DATASET.exists():
    DATASET = ROOT
FIELDS = (
    "inputVatInvoiceOrTaxReceipt", "nonCashPaymentForPurchase", "foreignPartyContract",
    "salesInvoice", "nonCashPaymentForExport", "customsDeclaration", "packingList",
    "billOfLading", "insuranceCertificate",
)
STATUSES = {"present", "absent", "unknown", "notApplicable"}
ACTIONS = {"limited_answer", "request_evidence", "human_review", "resolve_conflict",
           "out_of_scope", "request_time_context", "limited_answer_and_human_review"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    require(bool(rows), f"Empty dataset: {path}")
    return rows


def model_inputs(directory):
    """Explicit input-only API: never opens labels.jsonl."""
    return load_jsonl(directory / "cases.jsonl")


def predicate(statuses):
    return all(statuses[f] == "present" for f in FIELDS[:-1]) and statuses[FIELDS[-1]] in {"present", "notApplicable"}


def validate_records(cases, labels):
    require(len(cases) == len(labels), "Case/label counts differ")
    ids = [case["case_id"] for case in cases]
    require(len(set(ids)) == len(ids), "Duplicate case ID")
    require({label["case_id"] for label in labels} == set(ids) and len({label["case_id"] for label in labels}) == len(labels), "Label IDs differ or repeat")
    by_id = {label["case_id"]: label for label in labels}
    pins = None
    groups = {}
    for case in cases:
        case_id = case["case_id"]
        require(bool(re.fullmatch(r"PILOT-\d{3}", case_id)), "Invalid case ID")
        require(set(case) == {"case_id", "family_id", "split", "synthetic", "question", "context", "documents"}, "Unexpected input fields; possible label leakage")
        require(case["synthetic"] is True and case["split"] == "pilot_dev", "Pilot must remain synthetic development data")
        require(isinstance(case["question"], str) and bool(case["question"].strip()), "Missing question")
        require(isinstance(case["context"], dict), "Invalid case context")
        require(set(case["context"]) == {"transaction_kind", "business_date", "evaluation_mode", "scope_note"}, "Unexpected context fields; possible label leakage")
        group = groups.setdefault(case["family_id"], case["split"])
        require(group == case["split"], "Family split leakage")
        documents = {doc["document_id"]: doc for doc in case["documents"]}
        require(len(documents) == len(case["documents"]), "Duplicate document ID")
        for doc in documents.values():
            require(set(doc) == {"document_id", "kind", "content", "synthetic"}, "Unexpected document fields; possible label leakage")
            require(doc["synthetic"] is True and isinstance(doc["content"], str), "Document must be synthetic text")
        label = by_id[case_id]
        require(label["dataset_version"] == "pilot-v0.1", "Unexpected pilot version")
        require(label["family_id"] == case["family_id"] and label["split"] == case["split"], "Label/case identity differs")
        require(label["annotation"] == {"status": "draft", "author_kind": "assistant_generated_proposal", "reviewer_1": None, "reviewer_2": None, "adjudicator": None}, "Do not fabricate human review")
        require(label["online_eligible"] is False and label["legal_eligibility"] is None, "Pilot cannot declare legal eligibility")
        require(label["expected_action"] in ACTIONS, "Invalid expected action")
        require(label["rule_status"] == "candidate" and label["temporal_review"] == "pending", "Candidate rule must not be approved by pilot")
        require(set(label["evidence"]) == set(FIELDS), "Evidence slots differ from seed")
        for field, evidence in label["evidence"].items():
            require(evidence["status"] in STATUSES, f"Invalid status: {field}")
            require(bool(evidence["reason"].strip()), "Evidence reason required")
            require(bool(evidence["provenance"]), "Evidence provenance required")
            for ref in evidence["provenance"]:
                require(ref["document_id"] in documents and ref["paragraph"] == 1, "Evidence provenance locator missing")
            if evidence["status"] in {"absent", "notApplicable"}:
                require(evidence.get("status_basis") == "explicit_synthetic_attestation", "Absent/NA cannot be inferred from a search miss")
        eligible = label["lean_fixture_eligible"]
        require(type(eligible) is bool, "Fixture eligibility must be boolean")
        if eligible:
            require(case["context"]["transaction_kind"] == "ordinary_export_goods", "Seed does not cover services or special exports")
            require(not label["conflicts"], "Unresolved conflict must not become a Lean premise")
            require(case["context"]["evaluation_mode"] == "closed_source_snapshot", "Temporal questions require applicability review")
            expected = label["expected_demo_predicate"]
            require(type(expected) is bool, "Missing expected fixture result")
            require(predicate({key: item["status"] for key, item in label["evidence"].items()}) == expected, "Draft label disagrees with encoded seed")
        else:
            require(label["expected_demo_predicate"] is None, "Excluded fixture must not claim a proof outcome")
        for conflict in label["conflicts"]:
            require(conflict["field"] in FIELDS and label["evidence"][conflict["field"]]["status"] == "unknown", "Conflict must leave binding unresolved")
            require(all(doc in documents for doc in conflict["document_ids"]), "Conflict document missing")
        reference = label["reference"]
        require(reference["rule_id"] == "VAT_ART14_C2_EXPORT_DOCS" and reference["rule_version"] == "0.1.0-demo", "Wrong rule identity")
        require(reference["article"] == "14" and reference["clause"] == "2", "Wrong source provision")
        require({(r["point"], r["pdf_page"]) for r in reference["locators"]} == {("a", 15), ("b", 15), ("c", 16)}, "Wrong source page locators")
        if pins is None:
            pins = reference
        require(reference == pins, "Pilot source/rule snapshot differs across labels")
        require(bool(label["allowed_claims"]) and bool(label["forbidden_claims"]), "Missing claim boundaries")
    return {"status": "technical_checks_passed_not_legal_approval", "cases": len(cases),
            "families": len(groups), "pilot_dev": len(cases), "held_out": 0,
            "lean_fixture_eligible": sum(row["lean_fixture_eligible"] for row in labels),
            "draft_labels": len(labels), "human_reviewed_labels": 0,
            "online_eligible": 0, "abc_benchmark_executed": False}


def validate(directory, root=ROOT):
    cases = model_inputs(directory)
    labels = load_jsonl(directory / "labels.jsonl")
    result = validate_records(cases, labels)
    reference = labels[0]["reference"]
    for key in ("source", "lean_source"):
        artifact = reference[key]
        path = (root / artifact["path"]).resolve()
        require(path.is_relative_to(root.resolve()), "Pinned path leaves reference root")
        require(digest(path) == artifact["sha256"], f"Pinned artifact hash mismatch: {key}")
    result["cases_sha256"] = digest(directory / "cases.jsonl")
    result["labels_sha256"] = digest(directory / "labels.jsonl")
    return cases, labels, result


def check_lean(labels, root=ROOT):
    eligible = [label for label in labels if label["lean_fixture_eligible"]]
    require(bool(eligible), "No eligible technical fixtures")
    reference = labels[0]["reference"]
    source = root / reference["lean_source"]["path"]
    require(digest(source) == reference["lean_source"]["sha256"], "Lean source hash mismatch")
    code = source.read_text() + "\nnamespace VAT.Article14Clause2.Pilot\n"
    theorem_ids = []
    for label in eligible:
        name = label["case_id"].replace("-", "_")
        require(bool(re.fullmatch(r"PILOT_\d{3}", name)), "Unsafe generated Lean identifier")
        code += f"\ndef {name} : ExportGoodsEvidence where\n"
        for field in FIELDS:
            status = label["evidence"][field]["status"]
            require(status in STATUSES, "Unsafe Lean evidence status")
            code += f"  {field} := .{status}\n"
        target = f"SatisfiesDocumentConditions {name}"
        if not label["expected_demo_predicate"]:
            target = "¬ " + target
        theorem = name + "_expected"
        theorem_ids.append(theorem)
        code += f"theorem {theorem} : {target} := by\n  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition, {name}]\n"
        code += f"#print axioms {theorem}\n"
    code += "end VAT.Article14Clause2.Pilot\n"
    require(not re.search(r"\b(sorry|admit|axiom)\s+\w", code), "Generated source contains a proof placeholder or added axiom")
    with tempfile.TemporaryDirectory(prefix="da2-pilot-lean-") as temp:
        path = Path(temp) / "Pilot.lean"
        path.write_text(code)
        command = ["elan", "run", "leanprover/lean4:v4.33.1", "lean", str(path)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    require(result.returncode == 0, "Offline Lean fixture check failed: " + result.stdout + result.stderr)
    rows = re.findall(r"depends on axioms:\s*\[([^\]]*)\]", result.stdout)
    clean_rows = re.findall(r"does not depend on any axioms", result.stdout)
    require(len(rows) + len(clean_rows) == len(eligible), "Incomplete Lean axiom diagnostics")
    for row in rows:
        axioms = {item.strip().strip("'") for item in row.split(",") if item.strip()}
        require(axioms <= {"propext"}, "Unexpected Lean axiom dependency")
    return {"status": "offline_fixture_theorems_checked", "toolchain": "leanprover/lean4:v4.33.1",
            "checked_fixtures": len(eligible), "generated_source_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "theorems": theorem_ids, "axiom_diagnostics": result.stdout.strip(),
            "semantic_approval": False, "abc_benchmark_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET)
    parser.add_argument("--check-lean", action="store_true")
    args = parser.parse_args()
    _, labels, result = validate(args.dataset_dir)
    if args.check_lean:
        result["lean"] = check_lean(labels)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

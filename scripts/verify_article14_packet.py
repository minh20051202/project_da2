#!/usr/bin/env python3
"""Read-only technical verifier for the Article 14 demo packet.

Prints a JSON record to stdout; never approves a rule or edits artifacts.
Requires Python 3, pdftotext, elan, and the manifest's installed Lean toolchain.
"""

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PACKET = ROOT / "formalization/packets/VAT_ART14_C2_EXPORT_DOCS/v0.1.0"
FIELDS = (
    "inputVatInvoiceOrTaxReceipt", "nonCashPaymentForPurchase",
    "foreignPartyContract", "salesInvoice", "nonCashPaymentForExport",
    "customsDeclaration", "packingList", "billOfLading", "insuranceCertificate",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(command, input_text=None):
    return subprocess.run(
        command, input=input_text, text=True, capture_output=True,
        timeout=60, cwd=ROOT, check=False,
    )


def main():
    started = time.monotonic()
    record = {
        "schema_version": "demo-verification-record/1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "semantic_review": "pending",
        "approval": "not_approved",
        "online_eligible": False,
        "checks": {},
        "checker_sha256": sha256(Path(__file__)),
    }
    try:
        manifest = read_json(PACKET / "manifest.json")
        record["manifest_id"] = manifest["manifest_id"]
        record["manifest_sha256"] = sha256(PACKET / "manifest.json")
        record["toolchain"] = manifest["toolchain"]
        paths = {}
        for role, artifact in manifest["artifacts"].items():
            path = (ROOT / artifact["path"]).resolve()
            require(path.is_relative_to(ROOT), "Artifact path leaves project")
            require(sha256(path) == artifact["sha256"], "Hash mismatch: " + role)
            paths[role] = path
        record["checks"]["artifact_hashes"] = True

        source = read_json(paths["source_reference"])
        ir = read_json(paths["legal_ir"])
        mapping = read_json(paths["mapping_and_tests"])
        require(source["source_sha256"] == manifest["artifacts"]["legal_source"]["sha256"], "Source hash differs")
        require(source["source_path"] == manifest["artifacts"]["legal_source"]["path"], "Source path differs")
        require(ir["rule_id"] == mapping["rule_id"] == manifest["rule_id"], "Rule ID differs")
        require(ir["rule_version"] == manifest["rule_version"], "Rule version differs")
        require(mapping["namespace"] == manifest["namespace"], "Namespace differs")
        require(mapping["case_type"] == manifest["case_type"], "Case type differs")
        require(manifest["predicate_symbol"] == mapping["namespace"] + "." + mapping["target"], "Target differs")
        require(ir["condition_operator"] == "all_of", "Unexpected condition operator")
        for item in (ir, manifest):
            require(item["approval"] == "not_approved" and item["online_eligible"] is False, "Demo must not be approved")
            require(item["semantic_review"] == "pending", "Unreviewed demo status changed")
        record["checks"]["packet_identity_and_demo_status"] = True

        excerpts = {item["id"]: item for item in source["excerpts"]}
        for excerpt in excerpts.values():
            result = run([
                "pdftotext", "-f", str(excerpt["pdf_page"]), "-l",
                str(excerpt["pdf_page"]), "-layout", str(paths["legal_source"]), "-",
            ])
            require(result.returncode == 0, "PDF extraction failed: " + result.stderr)
            require(" ".join(excerpt["text"].split()) in " ".join(result.stdout.split()), "Excerpt differs from PDF: " + excerpt["id"])
        record["checks"]["source_excerpts_match_pdf_pages"] = True

        conditions = {item["id"]: item for item in ir["conditions"]}
        require(len(conditions) == len(ir["conditions"]) == len(FIELDS), "Condition IDs missing/duplicated")
        require(len(mapping["bindings"]) == len(FIELDS), "Unexpected binding count")
        require({b["lean_field"] for b in mapping["bindings"]} == set(FIELDS), "Lean fields differ")
        for binding in mapping["bindings"]:
            condition = conditions[binding["condition_id"]]
            for key in ("evidence_key", "accepted_statuses", "source_excerpt_id"):
                require(binding[key] == condition[key], "Condition/binding mismatch: " + key)
            require(binding["evidence_key"] == binding["lean_field"], "Unexpected field mapping")
            insurance = binding["lean_field"] == "insuranceCertificate"
            require(binding["accepted_statuses"] == (["present", "notApplicable"] if insurance else ["present"]), "Unexpected accepted statuses")
            require(binding["lean_predicate"] == ("insuranceCondition" if insurance else "isPresent"), "Unexpected predicate binding")
            require(binding["source_fragment"] in excerpts[binding["source_excerpt_id"]]["text"], "Source fragment differs")
        require([test["theorem"] for test in mapping["tests"]] == manifest["test_theorems"], "Test theorem list differs")
        require(len(mapping["tests"]) == 6, "Expected six regression cases")
        record["checks"]["ir_mapping_metadata_consistent"] = True

        lean_text = paths["lean_source"].read_text(encoding="utf-8")
        structure = re.search(r"structure ExportGoodsEvidence where\n(.*?)\n  deriving", lean_text, re.S)
        require(structure is not None, "Evidence structure missing")
        require(tuple(re.findall(r"^  (\w+) : EvidenceStatus$", structure.group(1), re.M)) == FIELDS, "Lean structure fields differ")
        require(not re.search(r"\b(sorry|admit|axiom)\b", lean_text), "Forbidden token in demo source")
        record["checks"]["demo_source_placeholder_scan"] = True

        lean_command = ["elan", "run", manifest["toolchain"], "lean"]
        version = run(lean_command + ["--version"])
        require(version.returncode == 0, "Lean version query failed")
        record["lean_version"] = version.stdout.strip()
        require("version 4.33.1," in record["lean_version"], "Unexpected Lean version")
        compile_command = lean_command + [str(paths["lean_source"].relative_to(ROOT))]
        compiled = run(compile_command)
        record["compile"] = {"command": compile_command, "exit_code": compiled.returncode, "stdout": compiled.stdout, "stderr": compiled.stderr}
        require(compiled.returncode == 0, "Lean compile failed")
        record["checks"]["lean_reelaboration"] = True

        probe = [lean_text]
        namespace = manifest["namespace"]
        for test in mapping["tests"]:
            target = manifest["predicate_symbol"] + " " + namespace + "." + test["case_symbol"]
            if not test["expected_predicate"]:
                target = "¬ (" + target + ")"
            probe.append("example : " + target + " := " + namespace + "." + test["theorem"])
            probe.append("#print axioms " + namespace + "." + test["theorem"])
        probed = run(lean_command + ["--stdin"], "\n".join(probe) + "\n")
        record["theorem_probe"] = {"exit_code": probed.returncode, "stdout": probed.stdout, "stderr": probed.stderr}
        require(probed.returncode == 0, "Expected theorem type probe failed")
        dependencies = {}
        for test in mapping["tests"]:
            symbol = namespace + "." + test["theorem"]
            axioms = re.search(r"'" + re.escape(symbol) + r"' depends on axioms: \[([^\]]*)\]", probed.stdout)
            if axioms:
                names = [name.strip() for name in axioms.group(1).split(",") if name.strip()]
            else:
                require("'" + symbol + "' does not depend on any axioms" in probed.stdout, "Axiom report missing: " + symbol)
                names = []
            require(set(names) <= set(manifest["axiom_allowlist"]), "Forbidden axiom dependency: " + symbol)
            dependencies[symbol] = names
        record["axiom_dependencies"] = dependencies
        record["test_count"] = len(mapping["tests"])
        record["checks"]["expected_theorem_types"] = True
        record["checks"]["axiom_dependency_allowlist"] = True

        # Keep original files untouched. First check the mutated predicate's
        # syntax/type, then ask the existing regressions to detect its error.
        mutations = (
            ("remove_customs_condition", "  isPresent e.customsDeclaration ∧\n", ""),
            ("allow_unknown_insurance", "status = .present ∨ status = .notApplicable", "status = .present ∨ status = .notApplicable ∨ status = .unknown"),
            ("allow_unknown_mandatory", "status = .present\n", "status = .present ∨ status = .unknown\n"),
        )
        mutation_results = []
        for name, old, new in mutations:
            require(lean_text.count(old) == 1, "Mutation anchor ambiguous: " + name)
            mutated = lean_text.replace(old, new, 1)
            core = mutated.split("/-- A synthetic case", 1)[0] + "\nend " + namespace + "\n"
            typed = run(lean_command + ["--stdin"], core)
            require(typed.returncode == 0, "Mutation is not well typed: " + name)
            tested = run(lean_command + ["--stdin"], mutated)
            require(tested.returncode != 0 and "unsolved goals" in tested.stdout, "Regression did not detect semantic mutation: " + name)
            mutation_results.append({
                "id": name, "predicate_typechecks": True,
                "regression_exit_code": tested.returncode,
                "detected": True,
            })
        record["mutation_smoke_tests"] = mutation_results
        record["checks"]["three_well_typed_mutations_detected"] = True
        record["status"] = "technical_checks_passed"
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        record["error"] = str(error)
    record["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "technical_checks_passed" else 1


if __name__ == "__main__":
    sys.exit(main())

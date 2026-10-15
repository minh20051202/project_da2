"""Regression tests for pilot data/contracts, not a benchmark of agent quality."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot_validator", ROOT / "scripts/validate_pilot_cases.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = pilot.model_inputs(pilot.DATASET)
        cls.labels = pilot.load_jsonl(pilot.DATASET / "labels.jsonl")

    def records(self):
        return copy.deepcopy(self.cases), copy.deepcopy(self.labels)

    def test_pilot_counts_are_not_final_benchmark_counts(self):
        result = pilot.validate_records(*self.records())
        self.assertEqual(result["cases"], 16)
        self.assertEqual(result["families"], 1)
        self.assertEqual(result["held_out"], 0)
        self.assertEqual(result["lean_fixture_eligible"], 11)
        self.assertEqual(result["human_reviewed_labels"], 0)
        self.assertFalse(result["abc_benchmark_executed"])

    def test_pinned_artifact_hashes_match_actual_sources(self):
        _, _, result = pilot.validate(pilot.DATASET, ROOT)
        self.assertEqual(result["online_eligible"], 0)

    def test_input_api_does_not_read_labels(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-input-only-") as temp:
            path = Path(temp)
            (path / "cases.jsonl").write_bytes((pilot.DATASET / "cases.jsonl").read_bytes())
            rows = pilot.model_inputs(path)
            self.assertEqual(len(rows), 16)

    def test_label_fields_cannot_leak_into_inputs(self):
        cases, labels = self.records()
        cases[0]["expected_action"] = labels[0]["expected_action"]
        with self.assertRaisesRegex(ValueError, "label leakage"):
            pilot.validate_records(cases, labels)

    def test_label_fields_cannot_leak_into_context(self):
        cases, labels = self.records()
        cases[0]["context"]["draft_label"] = labels[0]
        with self.assertRaisesRegex(ValueError, "label leakage"):
            pilot.validate_records(cases, labels)

    def test_duplicate_case_id_is_rejected(self):
        cases, labels = self.records()
        cases[1]["case_id"] = cases[0]["case_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate case"):
            pilot.validate_records(cases, labels)

    def test_variants_cannot_be_moved_into_held_out(self):
        cases, labels = self.records()
        cases[0]["split"] = labels[0]["split"] = "held_out"
        with self.assertRaisesRegex(ValueError, "development data"):
            pilot.validate_records(cases, labels)

    def test_provenance_must_resolve_to_real_input_document(self):
        cases, labels = self.records()
        labels[0]["evidence"]["customsDeclaration"]["provenance"][0]["document_id"] = "NONEXISTENT"
        with self.assertRaisesRegex(ValueError, "locator missing"):
            pilot.validate_records(cases, labels)

    def test_unknown_is_not_positive_predicate(self):
        cases, labels = self.records()
        self.assertEqual(labels[2]["evidence"]["customsDeclaration"]["status"], "unknown")
        labels[2]["expected_demo_predicate"] = True
        with self.assertRaisesRegex(ValueError, "disagrees"):
            pilot.validate_records(cases, labels)

    def test_absent_requires_explicit_basis(self):
        cases, labels = self.records()
        del labels[3]["evidence"]["customsDeclaration"]["status_basis"]
        with self.assertRaisesRegex(ValueError, "search miss"):
            pilot.validate_records(cases, labels)

    def test_insurance_na_and_unsupported_na_are_different(self):
        _, labels = self.records()
        self.assertEqual(labels[0]["evidence"]["insuranceCertificate"]["status"], "notApplicable")
        self.assertTrue(labels[0]["expected_demo_predicate"])
        self.assertEqual(labels[9]["evidence"]["insuranceCertificate"]["status"], "unknown")
        self.assertFalse(labels[9]["expected_demo_predicate"])
        self.assertFalse(labels[5]["lean_fixture_eligible"])

    def test_unresolved_conflict_cannot_be_bound_into_lean_fixture(self):
        cases, labels = self.records()
        labels[10]["lean_fixture_eligible"] = True
        labels[10]["expected_demo_predicate"] = False
        with self.assertRaisesRegex(ValueError, "Unresolved conflict"):
            pilot.validate_records(cases, labels)

    def test_service_case_cannot_use_goods_fixture(self):
        cases, labels = self.records()
        labels[12]["lean_fixture_eligible"] = True
        labels[12]["expected_demo_predicate"] = True
        with self.assertRaisesRegex(ValueError, "does not cover services"):
            pilot.validate_records(cases, labels)

    def test_draft_labels_cannot_be_marked_online_approved(self):
        cases, labels = self.records()
        labels[0]["online_eligible"] = True
        with self.assertRaisesRegex(ValueError, "legal eligibility"):
            pilot.validate_records(cases, labels)

    def test_human_review_must_not_be_fabricated(self):
        cases, labels = self.records()
        labels[0]["annotation"]["reviewer_1"] = "invented-reviewer"
        with self.assertRaisesRegex(ValueError, "fabricate human review"):
            pilot.validate_records(cases, labels)

    def test_full_refund_question_does_not_get_legal_eligibility(self):
        _, labels = self.records()
        self.assertTrue(labels[15]["expected_demo_predicate"])
        self.assertEqual(labels[15]["expected_action"], "limited_answer_and_human_review")
        self.assertIsNone(labels[15]["legal_eligibility"])


if __name__ == "__main__":
    unittest.main()

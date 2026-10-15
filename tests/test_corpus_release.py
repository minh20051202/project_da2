"""Technical integrity tests; not semantic or temporal legal validation."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("corpus_release", ROOT / "scripts/build_corpus_release.py")
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)


class CorpusReleaseTests(unittest.TestCase):
    def fixture(self, root):
        """Small generated corpus; test metadata/record gates without real PDF parsing."""
        release = root / "data/corpus/v0.1.1"
        release.mkdir(parents=True)
        (root / "sample.pdf").write_bytes(b"original-pdf")
        (root / "sample.docx").write_bytes(b"original-docx")
        legal_hash = corpus.sha256(b"original-pdf")
        business_hash = corpus.sha256(b"original-docx")
        legal = {"source_id": "LEGAL-001", "source_sha256": legal_hash,
                 "source_version_id": f"LEGAL-001@sha256:{legal_hash}",
                 "artifact_path": "sample.pdf", "pdf_pages": 1,
                 "effective_from": None, "effective_to": None, "online_eligible": False}
        business = {"source_id": "BUS-001", "sha256": business_hash,
                    "source_version_id": f"BUS-001@sha256:{business_hash}",
                    "artifact_path": "sample.docx", "paragraph_count": 1,
                    "real_enterprise_dossier": False, "online_legal_index_eligible": False}
        rows = []
        for source, text, kind, locator in ((legal, "Law text\n", "legal_pdf_page", "pdf_page"),
                                            (business, "Internal text", "internal_business_paragraph", "paragraph")):
            rows.append({"source_id": source["source_id"], "source_sha256": source.get("source_sha256", source.get("sha256")),
                         "source_version_id": source["source_version_id"], "text": text,
                         "text_sha256": corpus.sha256(text.encode()), "kind": kind, locator: 1})
        manifest = {"schema_version": "da2-source-corpus/2", "release_version": "v0.1.1",
                    "sources": [legal], "business_sources": [business],
                    "original_artifacts": [corpus.file_record("sample.pdf", b"original-pdf", "original_legal_pdf"),
                                           corpus.file_record("sample.docx", b"original-docx", "internal_business_design_docx")]}
        self.seal(release, manifest, rows)
        return release, manifest, rows

    def seal(self, release, manifest, rows):
        payload = {"pages.jsonl": corpus.jsonl_bytes(rows), "README.md": b"Test guide"}
        manifest.pop("release_id", None)
        manifest["derived_artifacts"] = [corpus.file_record(p, data, "derived") for p, data in payload.items()]
        manifest["release_id"] = f"corpus-{manifest['release_version']}-sha256:{corpus.sha256(corpus.json_bytes(manifest))}"
        for name, data in payload.items():
            (release / name).write_bytes(data)
        (release / "manifest.json").write_bytes(corpus.json_bytes(manifest))

    def test_pdf_page_numbers_keep_internal_blank_pages(self):
        self.assertEqual(corpus.split_pdf_pages("page1\f\fpage3\f"), ["page1", "", "page3"])

    def test_pdf_text_is_not_rewritten(self):
        text = "    Điều 14.  Điều kiện\n  a) Chứng từ;\n"
        self.assertEqual(corpus.split_pdf_pages(text + "\f"), [text])

    def test_reference_catalog_maps_exactly_37_sources(self):
        refs = corpus.read_reference_metadata(ROOT / corpus.REFERENCES)
        self.assertEqual(set(refs), set(range(1, 38)))
        self.assertIn("114/VBHN-VPQH", refs[1]["declared_title"])
        self.assertIn("219/2013", refs[28]["declared_title"])
        self.assertTrue(all(row["declared_source_url"] for row in refs.values()))

    def test_governance_sources_are_not_vat_answer_authorities(self):
        for number in range(24, 28):
            self.assertEqual(corpus.classify_scope(number), "system_governance_not_vat_answer_authority")

    def test_quality_queue_keeps_scan_mixed_and_filename_issues(self):
        item = {"scan_dominated": True, "low_text_pages": 10, "continuation_notices": [1]}
        self.assertIn("ocr_required", corpus.quality_issues(item, 3))
        self.assertIn("multiple_legal_documents_in_pdf_boundaries_need_review", corpus.quality_issues(item, 14))
        self.assertIn("filename_mismatch_only_amending_circular_present", corpus.quality_issues(item, 32))

    def test_same_release_is_idempotent_and_different_content_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-corpus-") as temp:
            destination = Path(temp) / "v0.1"
            payload = {"manifest.json": b"{}", "text/page.jsonl": b"original"}
            corpus.freeze_release(destination, payload)
            corpus.freeze_release(destination, payload)
            with self.assertRaisesRegex(ValueError, "different content"):
                corpus.freeze_release(destination, {"manifest.json": b"changed"})
            self.assertEqual((destination / "text/page.jsonl").read_bytes(), b"original")

    def test_changed_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-corpus-") as temp:
            release = Path(temp)
            (release / "manifest.json").write_text(json.dumps({"release_version": "v0.1", "release_id": "wrong"}))
            with self.assertRaisesRegex(ValueError, "Manifest identity"):
                corpus.verify_release(ROOT, release)

    def test_release_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Version"):
            corpus.build_payload(ROOT, "../../other")

    def test_compact_release_has_three_files_and_verifies_both_record_kinds(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            result = corpus.verify_release(root, release)
            self.assertEqual(len(list(release.iterdir())), 3)
            self.assertEqual(result["checked_pdf_pages"], 1)
            self.assertEqual(result["checked_business_paragraphs"], 1)

    def test_tampered_original_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            (root / "sample.pdf").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Artifact mismatch"):
                corpus.verify_release(root, release)

    def test_tampered_extraction_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            (release / "pages.jsonl").write_text("changed")
            with self.assertRaisesRegex(ValueError, "Artifact mismatch"):
                corpus.verify_release(root, release)

    def test_wrong_record_kind_cannot_promote_internal_text_to_legal_text(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, manifest, rows = self.fixture(root)
            rows[1]["kind"] = "legal_pdf_page"
            self.seal(release, manifest, rows)
            with self.assertRaisesRegex(ValueError, "provenance"):
                corpus.verify_release(root, release)

    def test_duplicate_locator_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, manifest, rows = self.fixture(root)
            rows.append(dict(rows[0]))
            self.seal(release, manifest, rows)
            with self.assertRaisesRegex(ValueError, "sequence"):
                corpus.verify_release(root, release)

    def test_wrong_source_version_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, manifest, rows = self.fixture(root)
            rows[0]["source_version_id"] = "different-version"
            self.seal(release, manifest, rows)
            with self.assertRaisesRegex(ValueError, "provenance"):
                corpus.verify_release(root, release)

    def test_unreviewed_legal_source_cannot_become_online_eligible(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, manifest, rows = self.fixture(root)
            manifest["sources"][0]["online_eligible"] = True
            self.seal(release, manifest, rows)
            with self.assertRaisesRegex(ValueError, "silently promoted"):
                corpus.verify_release(root, release)

    def test_extra_data_files_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-compact-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            (release / "duplicate.csv").write_text("redundant")
            with self.assertRaisesRegex(ValueError, "exactly three"):
                corpus.verify_release(root, release)

    def test_directory_export_is_self_contained_and_has_no_archive(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-folder-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            for name in ("scripts/build_corpus_release.py", "tests/test_corpus_release.py"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test fixture code")
            target = root / "delivery"
            corpus.export_release(root, release, target)
            corpus.export_release(root, release, target)
            result = corpus.verify_release(target, target / release.relative_to(root))
            self.assertEqual(result["checked_pdf_pages"], 1)
            self.assertFalse(list(target.rglob("*.zip")))
            self.assertTrue((target / "sample.pdf").is_file())
            self.assertTrue((target / "scripts/build_corpus_release.py").is_file())

    def test_directory_export_preserves_existing_edits(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-folder-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            for name in ("scripts/build_corpus_release.py", "tests/test_corpus_release.py"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test fixture code")
            target = root / "delivery"
            corpus.export_release(root, release, target)
            (target / "sample.pdf").write_bytes(b"user changes")
            with self.assertRaisesRegex(ValueError, "different content"):
                corpus.export_release(root, release, target)
            self.assertEqual((target / "sample.pdf").read_bytes(), b"user changes")

    def test_directory_export_rejects_workspace_and_release_targets(self):
        with tempfile.TemporaryDirectory(prefix="da2-test-folder-") as temp:
            root = Path(temp)
            release, _, _ = self.fixture(root)
            for target in (root, root.parent, release, release / "nested"):
                with self.assertRaisesRegex(ValueError, "must not replace"):
                    corpus.export_release(root, release, target)


if __name__ == "__main__":
    unittest.main()

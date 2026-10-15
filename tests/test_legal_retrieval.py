"""Structural/citation/filter tests. No measured LLM or legal-semantic accuracy."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import legal_retrieval as retrieval


class RetrievalTests(unittest.TestCase):
    def source(self):
        return {"source_id": "LEGAL-001", "source_version_id": "LEGAL-001@sha256:test",
                "source_sha256": "test", "artifact_path": "resources/sample.pdf",
                "pdf_pages": 2, "processing_status": "text_extracted_unreviewed",
                "quality_issues": ["semantic_review_pending", "temporal_review_pending"],
                "scope_group": "vat_core_and_amendments", "declared_title": "Luật mẫu",
                "effective_from": None, "effective_to": None}

    def pages(self):
        return [{"pdf_page": 1, "text": "  Điều 14. Khấu trừ\n  1. Phạm vi khác.\n  2. Điều kiện:\n  a) Có hóa đơn.\n  b) Có thanh toán.\n"},
                {"pdf_page": 2, "text": "  c) Có hợp đồng nước ngoài và tờ khai.\n  Điều 15. Hoàn thuế\n  1. Điều kiện hoàn.\n"}]

    def chunks(self):
        return retrieval.structural_chunks(self.source(), self.pages())

    def test_article_clause_point_metadata_and_page(self):
        chunks = self.chunks()
        c = next(row for row in chunks if row["article"] == "14" and row["clause"] == "2" and row["point"] == "c")
        self.assertEqual(c["pdf_page_start"], 2)
        self.assertIn("2. Điều kiện:", c["parent_context"])
        self.assertNotIn("Điều 15", c["text"])

    def test_raw_citation_matches_original_offsets_exactly(self):
        text = "\f".join(page["text"] for page in self.pages())
        for chunk in self.chunks():
            self.assertEqual(text[chunk["char_start"]:chunk["char_end"]], chunk["text"])
            self.assertEqual(retrieval.sha(chunk["text"].encode()), chunk["text_sha256"])

    def test_embedding_context_is_not_substituted_for_citation(self):
        c = next(row for row in self.chunks() if row["point"] == "c")
        self.assertIn("Luật mẫu", c["embedding_text"])
        self.assertNotIn("Luật mẫu", c["text"])

    def test_long_split_is_lossless_and_bounded(self):
        text = "Đoạn dài nhiều dòng.\n" * 300
        spans = retrieval.split_long(text, 0, len(text), 500)
        self.assertEqual("".join(text[a:b] for a, b in spans), text)
        self.assertTrue(all(b - a <= 500 for a, b in spans))

    def test_deterministic_chunk_identity(self):
        self.assertEqual(self.chunks(), self.chunks())

    def test_source_versions_do_not_collapse(self):
        source = self.source()
        original = self.chunks()
        source["source_version_id"] = "LEGAL-001@sha256:other"
        other = retrieval.structural_chunks(source, self.pages())
        self.assertNotEqual(original[0]["chunk_id"], other[0]["chunk_id"])

    def test_quoted_amendment_heading_does_not_become_main_article(self):
        pages = self.pages()
        pages[0]["text"] += '   “Điều 99. Văn bản sửa đổi được trích.\n'
        chunks = retrieval.structural_chunks(self.source(), pages)
        self.assertNotIn("99", {row["article"] for row in chunks})

    def test_scan_source_is_quarantined(self):
        source = self.source()
        source["processing_status"] = "ocr_required"
        with self.assertRaisesRegex(ValueError, "OCR"):
            retrieval.structural_chunks(source, self.pages())

    def test_mixed_document_pdf_is_quarantined(self):
        source = self.source()
        source["quality_issues"].append("multiple_legal_documents_in_pdf_boundaries_need_review")
        with self.assertRaisesRegex(ValueError, "Mixed"):
            retrieval.structural_chunks(source, self.pages())

    def test_governance_source_is_not_vat_answer_authority(self):
        source = self.source()
        source["scope_group"] = "system_governance_not_vat_answer_authority"
        with self.assertRaisesRegex(ValueError, "privacy"):
            retrieval.structural_chunks(source, self.pages())

    def test_keyword_normalizes_vietnamese_diacritics(self):
        self.assertEqual(retrieval.tokens("THUẾ GIÁ TRỊ GIA TĂNG, hóa đơn"), retrieval.tokens("thue gia tri gia tang hoa don"))

    def test_bm25_applies_eligible_set_before_ranking(self):
        chunks = self.chunks()
        lexical = retrieval.lexical_index(chunks)
        chosen = next(i for i, row in enumerate(chunks) if row["point"] == "a")
        ranked, _ = retrieval.bm25("hóa đơn", lexical, [chosen])
        self.assertEqual(ranked, [chosen])

    def test_offline_source_filter_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "Explicit"):
            retrieval.select_indices(self.chunks(), [], offline=True)
        self.assertEqual(retrieval.select_indices(self.chunks(), {"OTHER"}, offline=True), [])

    def test_online_unreviewed_source_is_blocked(self):
        self.assertEqual(retrieval.select_indices(self.chunks(), {"LEGAL-001"}, as_of="2026-10-15"), [])

    def test_missing_business_date_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "business date"):
            retrieval.select_indices(self.chunks(), {"LEGAL-001"})

    def test_invalid_business_date_is_rejected(self):
        with self.assertRaises(ValueError):
            retrieval.select_indices(self.chunks(), {"LEGAL-001"}, as_of="2026-99-99")

    def test_temporal_interval_is_end_exclusive(self):
        chunks = self.chunks()
        for c in chunks:
            c.update(online_eligible=True, effective_from="2026-01-01", effective_to="2026-07-01")
        self.assertTrue(retrieval.select_indices(chunks, {"LEGAL-001"}, as_of="2026-06-30"))
        self.assertEqual(retrieval.select_indices(chunks, {"LEGAL-001"}, as_of="2026-07-01"), [])

    def test_blocked_query_does_not_call_embedding_model(self):
        class NeverEmbed:
            def embed(self, *args, **kwargs):
                raise AssertionError("Must filter before embedding")
        chunks = self.chunks()
        result = retrieval.search("hóa đơn", chunks, np.zeros((len(chunks), 384)), {}, ["OTHER"], offline=True, encoder=NeverEmbed())
        self.assertEqual(result["status"], "no_eligible_sources")


if __name__ == "__main__":
    unittest.main()

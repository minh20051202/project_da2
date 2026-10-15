#!/usr/bin/env python3
"""Offline, source-version-pinned legal chunking + BM25/E5 retrieval prototype.

No LLM answers, legal approval, OCR, or implicit effective-date inference.
File indexes are an offline export, not a replacement for planned PostgreSQL/pgvector.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import hashlib
import json
import math
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np

from build_corpus_release import ROOT, VERSION, freeze_release, json_bytes, jsonl_bytes, verify_release
from download_embedding_model import MODEL_ID, REVISION

CORPUS = ROOT / "data/corpus" / VERSION
INDEX = ROOT / "data/retrieval/v0.1"
MODEL = ROOT / "models/multilingual-e5-small"
DEFAULT_SOURCES = ("LEGAL-001", "LEGAL-006", "LEGAL-010", "LEGAL-011", "LEGAL-012")
ARTICLE = re.compile(r"(?:^|(?<=\f))[ \t]*Điều[ \t]+(\d{1,3}[a-zđ]?)[.:][ \t]+([^\r\n]+)", re.M)
CLAUSE = re.compile(r"(?:^|(?<=\f))[ \t]*(\d{1,3})\.[ \t]+(?=\S)", re.M)
POINT = re.compile(r"(?:^|(?<=\f))[ \t]*([a-zđ](?:\d{1,2})?)\)[ \t]+(?=\S)", re.M)
SIGNATURE = re.compile(r"^[ \t]*(?:TM\.[ \t]*CHÍNH PHỦ|KT\.[ \t]*BỘ TRƯỞNG|CHỦ TỊCH QUỐC HỘI)[ \t]*$", re.M)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tokens(text):
    folded = unicodedata.normalize("NFKD", text.lower().replace("đ", "d"))
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", folded)


def split_long(text, start, end, cap=1400):
    spans = []
    while end - start > cap:
        stop = text.rfind("\n", start + cap // 2, start + cap)
        if stop < 0:
            stop = text.rfind(" ", start + cap // 2, start + cap)
        if stop < 0:
            stop = start + cap
        spans.append((start, stop))
        start = stop
    if start < end:
        spans.append((start, end))
    return spans


def structural_chunks(source, pages, cap=1400):
    """Candidate structural spans; preserve original raw text/offsets, never call them rules."""
    if source["processing_status"] == "ocr_required":
        raise ValueError("OCR-required source cannot enter the text index")
    if "multiple_legal_documents_in_pdf_boundaries_need_review" in source["quality_issues"]:
        raise ValueError("Mixed-document PDF requires document-boundary review before indexing")
    if source["scope_group"] == "system_governance_not_vat_answer_authority":
        raise ValueError("AI/privacy sources must not enter the VAT answer index")
    pages = sorted(pages, key=lambda x: x["pdf_page"])
    if [p["pdf_page"] for p in pages] != list(range(1, source["pdf_pages"] + 1)):
        raise ValueError("Incomplete extracted PDF page sequence")
    offsets, cursor = [], 0
    for page in pages:
        offsets.append(cursor)
        cursor += len(page["text"]) + 1
    text = "\f".join(page["text"] for page in pages)
    headings = list(ARTICLE.finditer(text))
    # The source corpus includes transition/amendment notes; for the primary
    # consolidated VAT Act the offline VAT index intentionally stops at Art 16.
    chunks = []
    for index, heading in enumerate(headings):
        article = heading[1]
        if source["source_id"] == "LEGAL-001" and int(re.match(r"\d+", article)[0]) > 16:
            continue
        astart = heading.start()
        aend = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        signature = SIGNATURE.search(text, heading.end(), aend)
        if signature:
            aend = signature.start()
        if aend <= astart:
            continue
        clauses = list(CLAUSE.finditer(text, heading.end(), aend))
        units = []
        if not clauses:
            units.append((astart, aend, None, None, "article", ""))
        else:
            units.append((astart, clauses[0].start(), None, None, "article_intro", ""))
            for ci, clause in enumerate(clauses):
                cend = clauses[ci + 1].start() if ci + 1 < len(clauses) else aend
                points = list(POINT.finditer(text, clause.end(), cend))
                if not points:
                    units.append((clause.start(), cend, clause[1], None, "clause", ""))
                else:
                    intro = text[clause.start():points[0].start()]
                    units.append((clause.start(), points[0].start(), clause[1], None, "clause_intro", ""))
                    for pi, point in enumerate(points):
                        pend = points[pi + 1].start() if pi + 1 < len(points) else cend
                        units.append((point.start(), pend, clause[1], point[1], "point", intro))
        for start, end, clause, point, kind, context in units:
            if not text[start:end].strip():
                continue
            spans = split_long(text, start, end, cap)
            for part, (begin, stop) in enumerate(spans, 1):
                raw = text[begin:stop]
                identity = f"{source['source_version_id']}:{begin}:{stop}:{sha(raw.encode())}"
                chunks.append({
                    "chunk_id": "chunk-" + sha(identity.encode())[:24],
                    "source_id": source["source_id"], "source_version_id": source["source_version_id"],
                    "source_sha256": source["source_sha256"], "source_path": source["artifact_path"],
                    "article": article, "clause": clause, "point": point, "kind": kind,
                    "article_title": heading[2].strip(), "part": part, "parts": len(spans),
                    "pdf_page_start": bisect.bisect_right(offsets, begin),
                    "pdf_page_end": bisect.bisect_right(offsets, max(begin, stop - 1)),
                    "char_start": begin, "char_end": stop, "text": raw, "text_sha256": sha(raw.encode()),
                    "parent_context": context,
                    "embedding_text": f"{source['declared_title']} | Điều {article}: {heading[2].strip()} | Khoản {clause or '-'} | Điểm {point or '-'}\n{context}\n{raw}",
                    "status": "structural_candidate_not_semantically_reviewed", "online_eligible": False,
                    "effective_from": source["effective_from"], "effective_to": source["effective_to"],
                    "quality_issues": source["quality_issues"],
                    "cross_reference_article_numbers": sorted(set(re.findall(r"Điều\s+(\d+[a-zđ]?)", raw))),
                })
    if not chunks:
        raise ValueError(f"No structural chunks for {source['source_id']}")
    return chunks


def lexical_index(chunks):
    postings = collections.defaultdict(list)
    lengths = []
    for row, chunk in enumerate(chunks):
        counts = collections.Counter(tokens(chunk["embedding_text"]))
        lengths.append(sum(counts.values()))
        for term, count in counts.items():
            postings[term].append([row, count])
    return {"algorithm": "BM25", "tokenizer": "vietnamese_accent_fold_word_v1", "k1": 1.5, "b": 0.75,
            "lengths": lengths, "avg_length": sum(lengths) / max(1, len(lengths)), "postings": dict(postings)}


def bm25(query, lexical, eligible):
    allowed = set(eligible)
    scores = collections.defaultdict(float)
    size = len(lexical["lengths"])
    for term in set(tokens(query)):
        hits = lexical["postings"].get(term, [])
        idf = math.log(1 + (size - len(hits) + 0.5) / (len(hits) + 0.5))
        for row, tf in hits:
            if row not in allowed:
                continue
            denominator = tf + lexical["k1"] * (1 - lexical["b"] + lexical["b"] * lexical["lengths"][row] / lexical["avg_length"])
            scores[row] += idf * tf * (lexical["k1"] + 1) / denominator
    return sorted(scores, key=lambda row: (-scores[row], row)), dict(scores)


class E5:
    def __init__(self, model_dir=MODEL):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id("<pad>"), pad_token="<pad>")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_dir / "model.onnx"), options, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.truncated = 0

    def embed(self, texts, kind="passage", batch_size=16):
        vectors = []
        for start in range(0, len(texts), batch_size):
            batch = self.tokenizer.encode_batch([kind + ": " + t for t in texts[start:start + batch_size]])
            self.truncated += sum(bool(item.overflowing) for item in batch)
            feeds = {"input_ids": np.array([i.ids for i in batch], dtype=np.int64),
                     "attention_mask": np.array([i.attention_mask for i in batch], dtype=np.int64)}
            if "token_type_ids" in self.inputs:
                feeds["token_type_ids"] = np.array([i.type_ids for i in batch], dtype=np.int64)
            hidden = self.session.run(None, {k: v for k, v in feeds.items() if k in self.inputs})[0]
            mask = feeds["attention_mask"][..., None]
            pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
            normalized = pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            vectors.append(normalized.astype(np.float32))
            if kind == "passage":
                print(f"Embedded {min(start + batch_size, len(texts))}/{len(texts)} chunks", flush=True)
        return np.concatenate(vectors) if vectors else np.empty((0, 384), dtype=np.float32)


def select_indices(chunks, source_ids, offline=False, as_of=None):
    if not source_ids:
        raise ValueError("Explicit source IDs are required; do not mix versions implicitly")
    if not offline and not as_of:
        raise ValueError("Online retrieval requires business date and approved temporal metadata")
    if as_of is not None:
        date.fromisoformat(as_of)
    return [i for i, row in enumerate(chunks) if row["source_id"] in source_ids and
            (offline or (row["online_eligible"] is True and row["effective_from"] is not None
                         and row["effective_from"] <= as_of and (row["effective_to"] is None or as_of < row["effective_to"])))]


def search(query, chunks, vectors, manifest, source_ids, mode="hybrid", offline=False, as_of=None, k=5, encoder=None):
    if not query.strip() or not 1 <= k <= 50:
        raise ValueError("Non-empty query and 1 <= k <= 50 required")
    eligible = select_indices(chunks, set(source_ids), offline, as_of)
    if not eligible:
        return {"status": "no_eligible_sources", "offline_snapshot": offline, "results": []}
    keyword, keyword_scores = bm25(query, manifest["lexical"], eligible)
    semantic = []
    if mode in {"semantic", "hybrid"}:
        encoder = encoder or E5()
        q = encoder.embed([query], kind="query")[0]
        scores = vectors[eligible] @ q
        semantic = [eligible[i] for i in np.argsort(-scores, kind="stable")]
    if mode == "keyword":
        ranked = keyword
    elif mode == "semantic":
        ranked = semantic
    elif mode == "hybrid":
        fused = collections.defaultdict(float)
        for ranking in (keyword[:50], semantic[:50]):
            for rank, index in enumerate(ranking, 1):
                fused[index] += 1 / (60 + rank)
        ranked = sorted(fused, key=lambda i: (-fused[i], i))
    else:
        raise ValueError("Unknown search mode")
    return {"status": "ok" if ranked else "no_match_in_selected_snapshot", "offline_snapshot": offline,
            "mode": mode, "legal_approval": "not_approved", "results": [
                {key: chunks[i][key] for key in ("chunk_id", "source_id", "source_version_id", "source_sha256", "source_path",
                                               "article", "clause", "point", "pdf_page_start", "pdf_page_end", "text", "parent_context", "status")}
                for i in ranked[:k]]}


def build(index=INDEX):
    started = time.monotonic()
    verify_release(ROOT, CORPUS)
    corpus = json.loads((CORPUS / "manifest.json").read_text())
    pages = collections.defaultdict(list)
    for line in (CORPUS / "pages.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["kind"] == "legal_pdf_page":
            pages[row["source_id"]].append(row)
    chunks = []
    selected = [s for s in corpus["sources"] if s["source_id"] in DEFAULT_SOURCES]
    for source in selected:
        chunks.extend(structural_chunks(source, pages[source["source_id"]]))
    encoder = E5()
    vectors = encoder.embed([chunk["embedding_text"] for chunk in chunks])
    import io
    buffer = io.BytesIO()
    np.save(buffer, vectors, allow_pickle=False)
    payload = {"chunks.jsonl": jsonl_bytes(chunks), "vectors.npy": buffer.getvalue()}
    model_files = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}
                   for path in sorted(MODEL.iterdir()) if path.is_file()]
    manifest = {"schema_version": "da2-legal-retrieval/1", "index_version": "v0.1",
                "corpus_release_id": corpus["release_id"], "corpus_manifest_sha256": sha((CORPUS / "manifest.json").read_bytes()),
                "selected_source_versions": {s["source_id"]: s["source_version_id"] for s in selected},
                "selection_policy": "Five clean-text primary VAT/procedure snapshots for offline development; not all 37 sources or legal approval.",
                "excluded_sources": [{"source_id": s["source_id"], "reason": s["quality_issues"] + ["not_selected_for_v0.1_offline_index"]}
                                     for s in corpus["sources"] if s["source_id"] not in DEFAULT_SOURCES],
                "chunk_count": len(chunks), "source_count": len(selected), "pdf_pages": sum(s["pdf_pages"] for s in selected),
                "dimension": int(vectors.shape[1]), "structural_parser": "article-clause-point-candidate-v1",
                "max_chunk_chars": 1400, "max_model_tokens": 512, "truncated_embedding_inputs": encoder.truncated,
                "model": {"id": MODEL_ID, "revision": REVISION, "variant": "official_onnx_qint8_avx512_vnni",
                          "pooling": "attention_mask_mean", "normalization": "L2", "prefixes": ["query: ", "passage: "],
                          "files": model_files, "license": "MIT", "card": "https://huggingface.co/intfloat/multilingual-e5-small"},
                "lexical": lexical_index(chunks), "fusion": "RRF k=60, top-50 from each channel",
                "online_eligible": False, "effective_dates_verified": False,
                "storage": "portable offline file index; production PostgreSQL/pgvector is not deployed in Week 4",
                "artifacts": {name: {"sha256": sha(raw), "bytes": len(raw)} for name, raw in payload.items()}}
    manifest["index_id"] = "index-v0.1-sha256:" + sha(json_bytes(manifest))
    payload["manifest.json"] = json_bytes(manifest)
    freeze_release(index, payload)
    print(json.dumps({"index": str(index), "chunk_count": len(chunks), "source_count": len(selected),
                      "dimension": manifest["dimension"], "elapsed_seconds": round(time.monotonic() - started, 3)}, indent=2))


def load_index(index=INDEX):
    manifest = json.loads((index / "manifest.json").read_text())
    identity = manifest.pop("index_id")
    if identity != "index-v0.1-sha256:" + sha(json_bytes(manifest)):
        raise ValueError("Index manifest identity mismatch")
    manifest["index_id"] = identity
    for name, item in manifest["artifacts"].items():
        if sha((index / name).read_bytes()) != item["sha256"]:
            raise ValueError("Index artifact hash mismatch: " + name)
    if sha((CORPUS / "manifest.json").read_bytes()) != manifest["corpus_manifest_sha256"]:
        raise ValueError("Corpus snapshot changed")
    for item in manifest["model"]["files"]:
        if sha((ROOT / item["path"]).read_bytes()) != item["sha256"]:
            raise ValueError("Embedding model hash mismatch")
    chunks = [json.loads(line) for line in (index / "chunks.jsonl").read_text().splitlines()]
    vectors = np.load(index / "vectors.npy", allow_pickle=False)
    if vectors.shape != (len(chunks), manifest["dimension"]) or not np.all(np.isfinite(vectors)):
        raise ValueError("Invalid vector matrix")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
        raise ValueError("Vectors are not L2 normalized")
    for chunk in chunks:
        if chunk["source_version_id"] != manifest["selected_source_versions"][chunk["source_id"]] or sha(chunk["text"].encode()) != chunk["text_sha256"]:
            raise ValueError("Chunk identity/provenance mismatch")
    return chunks, vectors, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    query = sub.add_parser("search")
    query.add_argument("--query", required=True)
    query.add_argument("--source-id", action="append", required=True)
    query.add_argument("--mode", choices=["keyword", "semantic", "hybrid"], default="hybrid")
    query.add_argument("--offline-snapshot", action="store_true")
    query.add_argument("--as-of")
    query.add_argument("--k", type=int, default=5)
    sub.add_parser("verify")
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        chunks, vectors, manifest = load_index()
        result = {"status": "index_integrity_checks_passed", "chunks": len(chunks), "index_id": manifest["index_id"]}
        if args.command == "search":
            result = search(args.query, chunks, vectors, manifest, args.source_id, args.mode, args.offline_snapshot, args.as_of, args.k)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""
Runs the full per-document pipeline (extract -> risk assess -> chunk+embed
into a document-scoped RAG index) in a background thread so the upload
endpoint can return immediately and the frontend can poll for live
progress, instead of blocking on a request for however long OCR takes.

Single responsibility: orchestrate the background job and persist its
results. The actual extraction/risk/RAG logic all lives in their own
phase packages — this just wires them together and reports progress.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from api import storage
from ingestion.pipeline import extract_document
from rag.chunker import chunk_document
from rag.embedder import Embedder
from rag.vector_store import VectorStore
from risk_model.predictor import assess_document

logger = logging.getLogger(__name__)

EXTRACTED_CACHE_DIR = Path(__file__).resolve().parent.parent / "storage" / "extracted"
EXTRACTED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
RAG_INDEX_DIR = Path(__file__).resolve().parent.parent / "storage" / "rag_indexes"
RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=2)

# A single shared embedder instance: loading MiniLM (or the fallback) is
# expensive enough that we don't want to redo it per upload.
_embedder_lock = threading.Lock()
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    with _embedder_lock:
        if _embedder is None:
            _embedder = Embedder()
            if _embedder.backend == "tfidf_svd":
                # Reuse the vocabulary/SVD fitted on the training corpus in
                # Phase 3 rather than re-fitting on a single new document
                # (which would produce a degenerate, overfit projection).
                if not _embedder.load_fallback():
                    logger.warning(
                        "No fitted fallback embedder found — per-document RAG "
                        "chat will be unavailable until `python3 -m rag.build_index` "
                        "has been run at least once."
                    )
        return _embedder


def submit_extraction_job(doc_id: str, pdf_path: str) -> None:
    _executor.submit(_run_pipeline, doc_id, pdf_path)


def _run_pipeline(doc_id: str, pdf_path: str) -> None:
    try:
        def progress(stage: str, current: int, total: int, message: str) -> None:
            pct_within_stage = (current / total * 100) if total else 0
            # Extraction is stages 0-70%, risk assessment 70-85%, RAG index 85-100%
            stage_offsets = {"loading": (0, 20), "ocr": (20, 60), "structuring": (60, 70)}
            lo, hi = stage_offsets.get(stage, (0, 70))
            overall_pct = lo + (hi - lo) * (pct_within_stage / 100)
            storage.update_progress(doc_id, "extracting", stage, overall_pct, message)

        storage.update_progress(doc_id, "extracting", "starting", 0, "Starting extraction")
        doc = extract_document(pdf_path, progress_callback=progress)

        with open(EXTRACTED_CACHE_DIR / f"{doc_id}.json", "w") as f:
            json.dump(doc.to_dict(), f)

        storage.update_progress(doc_id, "analyzing", "risk", 75, "Computing risk assessment")
        assessment = assess_document(doc)

        storage.update_progress(doc_id, "indexing", "chunking", 85, "Building searchable index")
        chunks = chunk_document(doc)
        embedder = get_embedder()
        if chunks:
            vectors = embedder.embed_texts([c.text for c in chunks])
            store = VectorStore(dim=vectors.shape[1])
            store.add(chunks, vectors)
            _save_doc_index(doc_id, store)

        storage.mark_ready(
            doc_id,
            page_count=doc.page_count,
            scanned_page_count=doc.scanned_page_count,
            section_count=len(doc.sections),
            risk_score=assessment.risk_score,
            risk_bucket=assessment.risk_bucket,
            extraction_warnings=doc.extraction_warnings,
        )
    except Exception as exc:
        logger.exception("Pipeline failed for document %s", doc_id)
        storage.mark_failed(doc_id, str(exc))


def _save_doc_index(doc_id: str, store: VectorStore) -> None:
    import faiss
    from dataclasses import asdict

    faiss.write_index(store.index, str(RAG_INDEX_DIR / f"{doc_id}.faiss"))
    with open(RAG_INDEX_DIR / f"{doc_id}.jsonl", "w") as f:
        for chunk in store.chunks:
            row = asdict(chunk)
            row["category"] = chunk.category.value
            f.write(json.dumps(row) + "\n")


def load_doc_index(doc_id: str) -> VectorStore | None:
    import faiss
    from ingestion.models import SectionCategory
    from rag.chunker import Chunk

    index_path = RAG_INDEX_DIR / f"{doc_id}.faiss"
    meta_path = RAG_INDEX_DIR / f"{doc_id}.jsonl"
    if not index_path.exists() or not meta_path.exists():
        return None

    store = VectorStore.__new__(VectorStore)
    store.index = faiss.read_index(str(index_path))
    store.dim = store.index.d
    store.chunks = []
    with open(meta_path) as f:
        for line in f:
            row = json.loads(line)
            row["category"] = SectionCategory(row["category"])
            store.chunks.append(Chunk(**row))
    return store


def load_extracted_document(doc_id: str) -> dict | None:
    path = EXTRACTED_CACHE_DIR / f"{doc_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

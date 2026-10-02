"""
Batched, resumable chunk extraction across the full local DPR corpus.
Run in batches (like Phase 2's build_corpus.py) so OCR-heavy documents
don't blow past a single invocation's time budget.

Usage: python3 -m rag.build_chunks --start 0 --end 9
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.pipeline import extract_document
from rag.chunker import chunk_document

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dprs"
RAW_CHUNKS_PATH = Path(__file__).resolve().parent / "index" / "raw_chunks.jsonl"
RAW_CHUNKS_PATH.parent.mkdir(exist_ok=True)

# Same cap used in Phase 2's corpus build, for the same reason (3 fully
# scanned 100-200+ page docs) and for consistency between the risk corpus
# and the RAG corpus.
MAX_OCR_PAGES = 8


def get_unique_files():
    pdf_files = sorted(DATA_DIR.rglob("*.pdf"))
    seen_names = set()
    unique_files = []
    for f in pdf_files:
        if f.name in seen_names:
            continue
        seen_names.add(f.name)
        unique_files.append(f)
    return unique_files


def build_chunks(start: int = 0, end: int | None = None):
    unique_files = get_unique_files()
    batch = unique_files[start:end]

    already_done = set()
    if RAW_CHUNKS_PATH.exists():
        with open(RAW_CHUNKS_PATH) as f:
            for line in f:
                already_done.add(json.loads(line)["source_file"])

    with open(RAW_CHUNKS_PATH, "a") as out:
        for i, pdf_path in enumerate(batch, start + 1):
            if pdf_path.name in already_done:
                print(f"[{i}/{len(unique_files)}] {pdf_path.name} ... SKIP (already chunked)")
                continue
            print(f"[{i}/{len(unique_files)}] {pdf_path.name} ...", flush=True)
            try:
                doc = extract_document(str(pdf_path), max_ocr_pages=MAX_OCR_PAGES)
                chunks = chunk_document(doc)
                for chunk in chunks:
                    row = asdict(chunk)
                    row["category"] = chunk.category.value
                    out.write(json.dumps(row) + "\n")
                out.flush()
                print(f"    OK  {len(chunks)} chunks", flush=True)
            except Exception as exc:
                print(f"    FAILED: {exc}", flush=True)

    print(f"\nBatch [{start}:{end}] done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()
    build_chunks(args.start, args.end)

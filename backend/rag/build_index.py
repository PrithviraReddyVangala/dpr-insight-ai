"""
Loads raw_chunks.jsonl, embeds every chunk, and builds+persists the FAISS
index. Separate from build_chunks.py so re-embedding (e.g. after swapping
embedding backends) doesn't require re-running PDF extraction/OCR.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.models import SectionCategory
from rag.chunker import Chunk
from rag.embedder import Embedder
from rag.vector_store import VectorStore

RAW_CHUNKS_PATH = Path(__file__).resolve().parent / "index" / "raw_chunks.jsonl"

BATCH_SIZE = 64


def load_raw_chunks() -> list[Chunk]:
    chunks = []
    with open(RAW_CHUNKS_PATH) as f:
        for line in f:
            row = json.loads(line)
            row["category"] = SectionCategory(row["category"])
            chunks.append(Chunk(**row))
    return chunks


def build_index():
    chunks = load_raw_chunks()
    print(f"Loaded {len(chunks)} chunks from {len(set(c.source_file for c in chunks))} documents")

    embedder = Embedder()
    print(f"Embedding backend: {embedder.backend}")

    if embedder.backend == "tfidf_svd":
        embedder.fit_fallback([c.text for c in chunks])

    store = VectorStore(dim=embedder.embed_query("warmup").shape[0])

    t0 = time.time()
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vectors = embedder.embed_texts([c.text for c in batch])
        store.add(batch, vectors)
        if (i // BATCH_SIZE) % 20 == 0:
            print(f"  embedded {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} "
                  f"[{time.time()-t0:.1f}s]", flush=True)

    store.save()
    print(f"\nIndex built: {store.index.ntotal} vectors, dim={store.dim}, "
          f"backend={embedder.backend}, total time={time.time()-t0:.1f}s")


if __name__ == "__main__":
    build_index()

"""
FAISS index wrapper: stores chunk embeddings for similarity search and
keeps the parallel chunk metadata needed to turn a search hit back into
readable, source-attributed text.

Single responsibility: vectors + metadata -> persisted searchable index.
No embedding computation, no chunking, lives here.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import faiss
import numpy as np

from rag.chunker import Chunk
from rag.embedder import EMBEDDING_DIM

INDEX_DIR = Path(__file__).resolve().parent / "index"
INDEX_DIR.mkdir(exist_ok=True)
FAISS_INDEX_PATH = INDEX_DIR / "chunks.faiss"
CHUNK_METADATA_PATH = INDEX_DIR / "chunks_metadata.jsonl"


class VectorStore:
    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors = cosine
        self.chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != vectors.shape[0]:
            raise ValueError("chunks/vectors length mismatch")
        if vectors.shape[0] == 0:
            return
        self.index.add(vectors)
        self.chunks.extend(chunks)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if self.index.ntotal == 0:
            return []
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        scores, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    def save(self) -> None:
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        with open(CHUNK_METADATA_PATH, "w") as f:
            for chunk in self.chunks:
                row = asdict(chunk)
                row["category"] = chunk.category.value
                f.write(json.dumps(row) + "\n")

    @classmethod
    def load(cls, dim: int = EMBEDDING_DIM) -> "VectorStore":
        from ingestion.models import SectionCategory

        store = cls(dim=dim)
        store.index = faiss.read_index(str(FAISS_INDEX_PATH))
        store.chunks = []
        with open(CHUNK_METADATA_PATH) as f:
            for line in f:
                row = json.loads(line)
                row["category"] = SectionCategory(row["category"])
                store.chunks.append(Chunk(**row))
        return store

    @staticmethod
    def exists_on_disk() -> bool:
        return FAISS_INDEX_PATH.exists() and CHUNK_METADATA_PATH.exists()

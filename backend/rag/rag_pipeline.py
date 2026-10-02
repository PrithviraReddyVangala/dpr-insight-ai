"""
Phase 3 entry point: the RAG query engine. Given a natural-language
question, retrieves the most relevant chunks from the FAISS index,
assembles them into a grounded prompt, and calls the LLM for an answer
with source attribution.

This is the module Phase 4's chat API will call.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag.embedder import Embedder
from rag.llm_client import LLMClient
from rag.vector_store import VectorStore

SYSTEM_PROMPT = (
    "You are the DPR Insight AI assistant. Answer the user's question about "
    "Detailed Project Reports (DPRs) using ONLY the excerpts provided in the "
    "context below. If the context doesn't contain the answer, say so plainly "
    "instead of guessing. Always cite which source file and heading an excerpt "
    "came from when you use it, using the format [filename — heading]."
)

DEFAULT_TOP_K = 6


@dataclass
class RetrievedChunk:
    text: str
    source_file: str
    heading_text: str
    category: str
    page_start: int
    page_end: int
    similarity: float


@dataclass
class RagAnswer:
    answer: str
    retrieved_chunks: list[RetrievedChunk]


class RagQueryEngine:
    def __init__(
        self,
        api_key: str | None = None,
        embedder: Embedder | None = None,
        store: VectorStore | None = None,
        skip_llm: bool = False,
    ):
        """embedder/store can be injected (e.g. Phase 4's API reuses a
        shared embedder instance and a per-document index) — if omitted,
        falls back to loading the Phase 3 training-corpus index from disk.
        skip_llm=True is for retrieval-only testing without an API key."""
        self.embedder = embedder or Embedder()
        if self.embedder.backend == "tfidf_svd" and self.embedder._vectorizer is None:
            if not self.embedder.load_fallback():
                raise RuntimeError(
                    "No fitted fallback embedder found on disk. Run "
                    "`python3 -m rag.build_index` first."
                )
        if store is not None:
            self.store = store
        else:
            if not VectorStore.exists_on_disk():
                raise RuntimeError("No FAISS index found on disk. Run `python3 -m rag.build_index` first.")
            self.store = VectorStore.load(dim=384)
        self.llm = None if skip_llm else LLMClient(api_key=api_key)

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K,
                 source_file: str | None = None) -> list[RetrievedChunk]:
        query_vector = self.embedder.embed_query(query)
        # over-fetch when filtering to a single document so we still end
        # up with top_k relevant results after filtering
        raw_top_k = top_k * 5 if source_file else top_k
        hits = self.store.search(query_vector, top_k=raw_top_k)

        results = []
        for chunk, score in hits:
            if source_file and chunk.source_file != source_file:
                continue
            results.append(
                RetrievedChunk(
                    text=chunk.text,
                    source_file=chunk.source_file,
                    heading_text=chunk.heading_text,
                    category=chunk.category.value,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    similarity=score,
                )
            )
            if len(results) >= top_k:
                break
        return results

    def _build_prompt(self, query: str, chunks: list[RetrievedChunk]) -> str:
        context_blocks = []
        for c in chunks:
            context_blocks.append(
                f"[{c.source_file} — {c.heading_text}] (pages {c.page_start+1}-{c.page_end+1}, "
                f"category={c.category})\n{c.text}"
            )
        context = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no relevant context found)"
        return f"Context:\n\n{context}\n\nQuestion: {query}"

    def query(self, query: str, top_k: int = DEFAULT_TOP_K, source_file: str | None = None) -> RagAnswer:
        chunks = self.retrieve(query, top_k=top_k, source_file=source_file)
        if self.llm is None:
            raise RuntimeError("This RagQueryEngine was constructed with skip_llm=True (retrieval only).")
        prompt = self._build_prompt(query, chunks)
        answer_text = self.llm.generate(prompt, system=SYSTEM_PROMPT)
        return RagAnswer(answer=answer_text, retrieved_chunks=chunks)

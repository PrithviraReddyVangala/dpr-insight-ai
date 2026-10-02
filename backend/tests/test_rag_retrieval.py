"""
Phase 3 validation: exercises retrieve() directly (the LLM generation
call needs ANTHROPIC_API_KEY, which isn't available in this sandbox — see
llm_client.py). Confirms the FAISS index returns genuinely relevant,
source-attributed chunks for different real queries across categories.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.rag_pipeline import RagQueryEngine

QUERIES = [
    "What is the estimated project cost and financial breakdown?",
    "What is the implementation timeline and project schedule?",
    "What environmental clearances are required?",
    "What is the scope of work for this project?",
    "What are the technical specifications and design standards?",
]


def run():
    from rag.embedder import Embedder
    from rag.vector_store import VectorStore

    embedder = Embedder()
    if embedder.backend == "tfidf_svd":
        embedder.load_fallback()
    store = VectorStore.load(dim=384)
    engine = RagQueryEngine(embedder=embedder, store=store, skip_llm=True)

    for query in QUERIES:
        print("=" * 90)
        print(f"QUERY: {query}")
        results = engine.retrieve(query, top_k=3)
        for r in results:
            preview = r.text[:120].replace("\n", " ")
            print(f"  [{r.category:11s} sim={r.similarity:.3f}] {r.source_file} — {r.heading_text[:50]}")
            print(f"      {preview}...")
        print()


if __name__ == "__main__":
    run()

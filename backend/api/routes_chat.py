"""
RAG chat endpoint: answers questions grounded in one specific uploaded
document's own content (the "interactive RAG chat drawer" from the
architecture spec) using that document's dedicated FAISS index built
during the background pipeline.

Single responsibility: HTTP concerns for chat. Retrieval/generation logic
lives in rag/rag_pipeline.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import jobs, storage
from api.schemas import ChatRequest, ChatResponse, RetrievedChunkOut
from rag.rag_pipeline import RagQueryEngine

router = APIRouter(prefix="/api/documents", tags=["chat"])


@router.post("/{doc_id}/chat", response_model=ChatResponse)
def chat_with_document(doc_id: str, request: ChatRequest):
    record = storage.get_document(doc_id)
    if not record:
        raise HTTPException(404, "Document not found")
    if record.status != "ready":
        raise HTTPException(409, f"Document is not ready yet (status={record.status})")

    store = jobs.load_doc_index(doc_id)
    if store is None or store.index.ntotal == 0:
        raise HTTPException(
            409, "This document has no searchable content (extraction may have "
                 "found no text) — chat isn't available for it."
        )

    embedder = jobs.get_embedder()
    try:
        engine = RagQueryEngine(embedder=embedder, store=store)
    except RuntimeError as exc:
        # Most likely: no GEMINI_API_KEY configured in this environment.
        raise HTTPException(503, f"Chat is unavailable: {exc}")

    try:
        result = engine.query(request.query, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(502, f"LLM request failed: {exc}")

    return ChatResponse(
        answer=result.answer,
        retrieved_chunks=[RetrievedChunkOut(**vars(c)) for c in result.retrieved_chunks],
    )

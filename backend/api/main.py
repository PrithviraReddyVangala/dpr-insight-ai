"""
DPR Insight AI backend API. Ties together ingestion (Phase 1), the risk
model (Phase 2), and RAG (Phase 3) behind a small set of REST endpoints
for the dashboard frontend (Phase 5).

No auth, no login pages — per the project's explicit scope constraints,
this is a single-user local tool.

Run with: uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import routes_chat, routes_documents, routes_risk

app = FastAPI(
    title="DPR Insight AI API",
    description="Automated evaluation, risk prediction, and RAG assistant for Detailed Project Reports.",
    version="0.4.0",
)

# The frontend (Vite dev server) runs on a different origin locally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_documents.router)
app.include_router(routes_risk.router)
app.include_router(routes_chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

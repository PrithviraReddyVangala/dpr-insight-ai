"""
Pydantic schemas for API request/response bodies. Kept separate from
route handlers per single-responsibility — routes stay focused on HTTP
concerns, schemas define the wire contract.
"""

from __future__ import annotations

from pydantic import BaseModel


class DocumentSummary(BaseModel):
    id: str
    original_filename: str
    status: str
    progress_stage: str | None
    progress_pct: float
    progress_message: str | None
    error_message: str | None
    page_count: int | None
    scanned_page_count: int | None
    section_count: int | None
    risk_score: float | None
    risk_bucket: str | None
    extraction_warnings: list[str]
    created_at: float


class UploadResponse(BaseModel):
    id: str
    status: str
    message: str


class SectionOut(BaseModel):
    heading_text: str
    category: str
    page_start: int
    page_end: int
    char_count: int
    text: str


class DocumentDetail(DocumentSummary):
    sections: list[SectionOut]


class FeatureContributionOut(BaseModel):
    feature: str
    value: float
    shap_contribution: float


class RiskDetail(BaseModel):
    risk_score: float
    risk_bucket: str
    bucket_probabilities: dict[str, float]
    top_contributions: list[FeatureContributionOut]
    base_value: float
    methodology_note: str = (
        "This score reflects documentation completeness and compliance-readiness "
        "as extracted from the DPR's own text (presence of financials/timeline/"
        "clearances/technical sections, quantified figures, clearance references, "
        "scan quality) — it is not a validated predictor of real-world project "
        "outcomes such as delays or cost overruns."
    )


class ChatRequest(BaseModel):
    query: str
    top_k: int = 6


class RetrievedChunkOut(BaseModel):
    text: str
    source_file: str
    heading_text: str
    category: str
    page_start: int
    page_end: int
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    retrieved_chunks: list[RetrievedChunkOut]

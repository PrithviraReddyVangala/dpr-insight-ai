"""
Risk assessment endpoint: returns the dynamic SHAP-based breakdown for a
ready document. Recomputes from the cached extraction rather than trusting
only the summary fields stored on the document row, so the full
per-feature contribution list (which isn't persisted in SQLite) is always
fresh.

Single responsibility: HTTP concerns for risk. Model logic lives in
risk_model/predictor.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import jobs, storage
from api.schemas import FeatureContributionOut, RiskDetail
from ingestion.models import ExtractedDocument, PageDiagnostics, Section, SectionCategory
from risk_model.predictor import assess_document

router = APIRouter(prefix="/api/documents", tags=["risk"])


def _rehydrate_document(doc_id: str, extracted: dict) -> ExtractedDocument:
    sections = [
        Section(
            heading_text=s["heading_text"],
            category=SectionCategory(s["category"]),
            page_start=s["page_start"],
            page_end=s["page_end"],
            text=s["text"],
        )
        for s in extracted["sections"]
    ]
    diagnostics = [
        PageDiagnostics(
            page_number=p["page_number"],
            char_count=p["char_count"],
            is_scanned=p["is_scanned"],
            ocr_applied=p["ocr_applied"],
        )
        for p in extracted["page_diagnostics"]
    ]
    return ExtractedDocument(
        source_path=extracted["source_path"],
        filename=extracted["filename"],
        page_count=extracted["page_count"],
        body_font_size=extracted["body_font_size"],
        sections=sections,
        page_diagnostics=diagnostics,
        scanned_page_count=extracted["scanned_page_count"],
        extraction_warnings=extracted["extraction_warnings"],
    )


@router.get("/{doc_id}/risk", response_model=RiskDetail)
def get_risk(doc_id: str):
    record = storage.get_document(doc_id)
    if not record:
        raise HTTPException(404, "Document not found")
    if record.status != "ready":
        raise HTTPException(409, f"Document is not ready yet (status={record.status})")

    extracted = jobs.load_extracted_document(doc_id)
    if extracted is None:
        raise HTTPException(500, "Document marked ready but extraction cache is missing")

    doc = _rehydrate_document(doc_id, extracted)
    assessment = assess_document(doc)

    return RiskDetail(
        risk_score=assessment.risk_score,
        risk_bucket=assessment.risk_bucket,
        bucket_probabilities=assessment.bucket_probabilities,
        top_contributions=[FeatureContributionOut(**vars(c)) for c in assessment.top_contributions],
        base_value=assessment.base_value,
    )

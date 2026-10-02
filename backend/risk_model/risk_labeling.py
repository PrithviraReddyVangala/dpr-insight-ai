"""
IMPORTANT METHODOLOGICAL NOTE
==============================
The local dataset is 33 real government DPR PDFs with NO ground-truth
outcome labels attached (no recorded cost overruns, delays, rejection/
approval history, audit findings, etc. — that data doesn't exist in this
corpus). Training a supervised model therefore requires SOME target to
fit against.

Rather than fabricate a random/fake label column (which would be exactly
the kind of mock behavior this project explicitly forbids), this module
computes a transparent, rule-based COMPLETENESS & COMPLIANCE-READINESS
risk proxy directly from each document's own extracted features: are the
canonical sections present, are financial figures actually quantified,
are clearance references substantive, how scan-degraded is the source,
etc. This becomes the weak-supervision target.

The RandomForest/XGBoost model trained on top of this (risk_trainer.py)
then LEARNS to approximate and generalize this rubric from raw features,
which is what makes SHAP feature-importance breakdowns meaningful and
document-specific rather than just re-outputting the rubric verbatim.

This is a legitimate, standard technique (weak supervision) — but it is
NOT the same as a model trained on real-world project outcomes. The risk
score this pipeline produces should be read as "how complete and
compliance-ready does this DPR's documentation appear", not "will this
project fail". If real outcome data (delays, cost overruns, audit
results) becomes available later, risk_trainer.py should be re-pointed
at that instead of this rubric.
"""

from __future__ import annotations

from enum import Enum

from ingestion.models import ExtractedDocument, SectionCategory

# Weak-label formula weights. Each contributes 0..its max to a 0-100
# risk score. Missing a canonical section is weighted heaviest because an
# absent Financials or Clearances section is the single strongest
# real-world red flag reviewers look for in a DPR completeness check.
_MISSING_SECTION_PENALTY = {
    SectionCategory.FINANCIALS: 20,
    SectionCategory.CLEARANCES: 20,
    SectionCategory.TIMELINE: 12,
    SectionCategory.TECHNICAL: 10,
    SectionCategory.SCOPE: 8,
}
_MAX_MISSING_PENALTY = sum(_MISSING_SECTION_PENALTY.values())  # 70

_VAGUE_FINANCIALS_PENALTY = 12       # has a Financials section but few actual figures/currency mentions
_VAGUE_CLEARANCES_PENALTY = 10       # has a Clearances section but few substantive compliance keywords
_SCAN_DEGRADATION_MAX_PENALTY = 8    # scaled by scanned_page_ratio
_IMBALANCE_MAX_PENALTY = 6           # scaled by section_balance_std (very lopsided documents)

_FINANCIAL_DENSITY_FLOOR = 2.0       # currency/number hits per 1000 chars, below which "vague"
_CLEARANCE_DENSITY_FLOOR = 1.5       # keyword hits per 1000 chars, below which "vague"

_LOW_RISK_MAX = 30
_MEDIUM_RISK_MAX = 60


class RiskBucket(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def compute_risk_label(doc: ExtractedDocument, features: dict[str, float]) -> tuple[float, RiskBucket]:
    """Returns (risk_score 0-100, bucket). Pure function of already-computed
    features so this stays consistent with what the model sees."""
    score = 0.0

    for category, penalty in _MISSING_SECTION_PENALTY.items():
        has_key = f"has_{category.value}"
        if features.get(has_key, 0.0) < 1.0:
            score += penalty

    if features.get("has_financials", 0.0) >= 1.0 and features.get("financial_numeric_density", 0.0) < _FINANCIAL_DENSITY_FLOOR:
        score += _VAGUE_FINANCIALS_PENALTY

    if features.get("has_clearances", 0.0) >= 1.0 and features.get("clearance_keyword_density", 0.0) < _CLEARANCE_DENSITY_FLOOR:
        score += _VAGUE_CLEARANCES_PENALTY

    score += min(_SCAN_DEGRADATION_MAX_PENALTY, features.get("scanned_page_ratio", 0.0) * _SCAN_DEGRADATION_MAX_PENALTY)

    # section_balance_std for 5 ratios that sum to <=1 rarely exceeds ~0.35;
    # normalize against that ceiling so the penalty scales sensibly.
    imbalance = min(1.0, features.get("section_balance_std", 0.0) / 0.35)
    score += imbalance * _IMBALANCE_MAX_PENALTY

    score = max(0.0, min(100.0, score))

    if score <= _LOW_RISK_MAX:
        bucket = RiskBucket.LOW
    elif score <= _MEDIUM_RISK_MAX:
        bucket = RiskBucket.MEDIUM
    else:
        bucket = RiskBucket.HIGH

    return score, bucket

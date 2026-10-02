"""
Phase 2 inference entry point: given an ExtractedDocument (from Phase 1),
produce a risk score, bucket, and a SHAP-based feature contribution
breakdown that is computed fresh from that document's own feature vector
— so it varies document-to-document by construction, not by design intent
alone. This is the module Phase 4's API will call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import shap

from ingestion.models import ExtractedDocument
from risk_model.feature_builder import FEATURE_NAMES, build_feature_vector

MODEL_DIR = Path(__file__).resolve().parent / "trained"
BUCKET_ORDER = ["low", "medium", "high"]

_classifier = None
_regressor = None
_explainer = None


def _load_models():
    global _classifier, _regressor, _explainer
    if _classifier is None:
        _classifier = joblib.load(MODEL_DIR / "risk_classifier.joblib")
        _regressor = joblib.load(MODEL_DIR / "risk_regressor.joblib")
        _explainer = shap.TreeExplainer(_regressor)
    return _classifier, _regressor, _explainer


@dataclass
class FeatureContribution:
    feature: str
    value: float
    shap_contribution: float  # signed: positive = pushes risk score up


@dataclass
class RiskAssessment:
    risk_score: float
    risk_bucket: str
    bucket_probabilities: dict[str, float]
    top_contributions: list[FeatureContribution]
    base_value: float  # the regressor's expected value before this doc's features are applied


def assess_document(doc: ExtractedDocument) -> RiskAssessment:
    classifier, regressor, explainer = _load_models()

    features = build_feature_vector(doc)
    x = np.array([[features[name] for name in FEATURE_NAMES]])

    score = float(regressor.predict(x)[0])
    score = max(0.0, min(100.0, score))

    bucket_idx = int(classifier.predict(x)[0])
    bucket_proba = classifier.predict_proba(x)[0]
    bucket_probabilities = {BUCKET_ORDER[i]: float(p) for i, p in enumerate(bucket_proba)}

    shap_values = explainer.shap_values(x)[0]  # one value per feature, for this document
    expected_value = explainer.expected_value
    base_value = float(np.ravel(expected_value)[0])

    contributions = [
        FeatureContribution(feature=name, value=float(features[name]), shap_contribution=float(sv))
        for name, sv in zip(FEATURE_NAMES, shap_values)
    ]
    contributions.sort(key=lambda c: abs(c.shap_contribution), reverse=True)

    return RiskAssessment(
        risk_score=round(score, 1),
        risk_bucket=BUCKET_ORDER[bucket_idx],
        bucket_probabilities={k: round(v, 3) for k, v in bucket_probabilities.items()},
        top_contributions=contributions[:8],
        base_value=round(base_value, 2),
    )

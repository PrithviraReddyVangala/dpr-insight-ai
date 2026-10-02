"""
Turns a Phase-1 ExtractedDocument into a fixed-length numeric feature
vector for the risk model. Every feature here is computed from the
document's own extracted content — nothing is hardcoded or templated per
file, so two different DPRs always produce different vectors.

Single responsibility: ExtractedDocument -> dict[str, float]. No model
training, no labeling logic lives here (see risk_labeling.py for that).
"""

from __future__ import annotations

import re
from statistics import pstdev

from ingestion.models import ExtractedDocument, SectionCategory

# Regex signals used to measure how *substantive* a section's content is,
# not just how long it is (a vague paragraph and a real costed table both
# have length, but only one has numbers/keywords backing it up).
_CURRENCY_NUMERIC_PATTERN = re.compile(
    r"(rs\.?\s?\d|inr\s?\d|₹\s?\d|\blakh(s)?\b|\bcrore(s)?\b|\b\d{1,3}(,\d{2,3})+(\.\d+)?\b|\b\d+(\.\d+)?\s?%)",
    re.IGNORECASE,
)
_TIMELINE_NUMERIC_PATTERN = re.compile(
    r"(\bphase\s?[iv0-9]+\b|\bmonth(s)?\b|\byear(s)?\b|\bq[1-4]\b|\bweek(s)?\b|\b20\d{2}\b|\bmilestone\b)",
    re.IGNORECASE,
)
_CLEARANCE_KEYWORD_PATTERN = re.compile(
    r"(environmental clearance|forest clearance|\bnoc\b|no objection|statutory|"
    r"consent to establish|consent to operate|land acquisition|right of way|"
    r"government order|\bsanction(ed)?\b|\bauthoriz(e|ation)|\bapprov(ed|al)\b)",
    re.IGNORECASE,
)

CATEGORIES = [
    SectionCategory.FINANCIALS,
    SectionCategory.TIMELINE,
    SectionCategory.SCOPE,
    SectionCategory.CLEARANCES,
    SectionCategory.TECHNICAL,
]

FEATURE_NAMES = [
    "page_count",
    "total_sections",
    "scanned_page_ratio",
    "total_chars_log",
    "financial_char_ratio",
    "timeline_char_ratio",
    "scope_char_ratio",
    "clearances_char_ratio",
    "technical_char_ratio",
    "other_char_ratio",
    "has_financials",
    "has_timeline",
    "has_scope",
    "has_clearances",
    "has_technical",
    "financial_numeric_density",
    "clearance_keyword_density",
    "timeline_numeric_density",
    "section_balance_std",
    "avg_section_length_log",
    "num_financial_sections",
    "num_clearance_sections",
]


def _category_text(doc: ExtractedDocument, category: SectionCategory) -> str:
    return "\n".join(s.text for s in doc.sections if s.category == category)


def _density_per_1000_chars(pattern: re.Pattern, text: str) -> float:
    if not text:
        return 0.0
    hits = len(pattern.findall(text))
    return hits / (len(text) / 1000.0)


def build_feature_vector(doc: ExtractedDocument) -> dict[str, float]:
    import math

    total_chars = sum(s.char_count for s in doc.sections) or 1
    cat_chars = {cat: sum(s.char_count for s in doc.sections if s.category == cat) for cat in CATEGORIES}
    cat_ratios = {cat: cat_chars[cat] / total_chars for cat in CATEGORIES}

    financial_text = _category_text(doc, SectionCategory.FINANCIALS)
    clearance_text = _category_text(doc, SectionCategory.CLEARANCES)
    timeline_text = _category_text(doc, SectionCategory.TIMELINE)

    scanned_ratio = doc.scanned_page_count / max(doc.page_count, 1)
    section_lengths = [s.char_count for s in doc.sections] or [0]

    features = {
        "page_count": float(doc.page_count),
        "total_sections": float(len(doc.sections)),
        "scanned_page_ratio": scanned_ratio,
        "total_chars_log": math.log1p(total_chars),
        "financial_char_ratio": cat_ratios[SectionCategory.FINANCIALS],
        "timeline_char_ratio": cat_ratios[SectionCategory.TIMELINE],
        "scope_char_ratio": cat_ratios[SectionCategory.SCOPE],
        "clearances_char_ratio": cat_ratios[SectionCategory.CLEARANCES],
        "technical_char_ratio": cat_ratios[SectionCategory.TECHNICAL],
        "other_char_ratio": max(0.0, 1.0 - sum(cat_ratios.values())),
        "has_financials": float(cat_chars[SectionCategory.FINANCIALS] > 200),
        "has_timeline": float(cat_chars[SectionCategory.TIMELINE] > 200),
        "has_scope": float(cat_chars[SectionCategory.SCOPE] > 200),
        "has_clearances": float(cat_chars[SectionCategory.CLEARANCES] > 200),
        "has_technical": float(cat_chars[SectionCategory.TECHNICAL] > 200),
        "financial_numeric_density": _density_per_1000_chars(_CURRENCY_NUMERIC_PATTERN, financial_text),
        "clearance_keyword_density": _density_per_1000_chars(_CLEARANCE_KEYWORD_PATTERN, clearance_text),
        "timeline_numeric_density": _density_per_1000_chars(_TIMELINE_NUMERIC_PATTERN, timeline_text),
        "section_balance_std": pstdev(list(cat_ratios.values())) if len(cat_ratios) > 1 else 0.0,
        "avg_section_length_log": math.log1p(sum(section_lengths) / len(section_lengths)),
        "num_financial_sections": float(len([s for s in doc.sections if s.category == SectionCategory.FINANCIALS])),
        "num_clearance_sections": float(len([s for s in doc.sections if s.category == SectionCategory.CLEARANCES])),
    }
    return features

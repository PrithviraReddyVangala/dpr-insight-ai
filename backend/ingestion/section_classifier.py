"""
Classifies a detected heading's text into one of the five canonical DPR
sub-section categories the ML and RAG pipelines are built around, or OTHER
if nothing matches confidently.

Single responsibility: text -> category. Pure function, no PDF/font
concerns, so it can be unit tested against strings directly and reused
by the RAG chunk-tagging step later.
"""

from __future__ import annotations

import re

from .models import SectionCategory

# Keyword sets derived from scanning real DPR structures across the sample
# corpus (PMGSY bridge DPRs, MKSP livelihoods DPRs, data-centre DPRs, road
# DPRs) — these documents don't share a single template, so classification
# has to work off vocabulary rather than fixed heading numbers.
_CATEGORY_KEYWORDS: dict[SectionCategory, list[str]] = {
    SectionCategory.FINANCIALS: [
        "financial", "finance", "cost", "budget", "estimate", "expenditure",
        "funding", "fund requirement", "abstract of cost", "boq",
        "bill of quantities", "rate analysis", "economic analysis",
        "financial viability", "revenue", "investment", "capital cost",
        "recurring cost", "cost benefit", "loan", "subsidy", "grant",
        "financial inclusion", "outlay",
    ],
    SectionCategory.TIMELINE: [
        "timeline", "schedule", "implementation plan", "phasing",
        "time frame", "milestone", "work plan", "duration", "completion period",
        "gantt", "phase i", "phase ii", "year 1", "year-wise", "annual plan",
        "project period", "commencement",
    ],
    SectionCategory.SCOPE: [
        "scope of work", "scope", "project background", "objective",
        "rationale", "project description", "introduction", "background",
        "context", "project at a glance", "executive summary", "overview",
        "beneficiar", "target group", "coverage area", "project area",
        "demographic", "need assessment", "justification", "component",
    ],
    SectionCategory.CLEARANCES: [
        "clearance", "approval", "environmental clearance", "forest clearance",
        "noc", "no objection", "statutory", "compliance", "permission",
        "consent", "regulatory", "land acquisition", "right of way",
        "government order", "sanction", "authorization", "authorisation",
    ],
    SectionCategory.TECHNICAL: [
        "technical", "design", "specification", "survey", "investigation",
        "drawing", "methodology", "engineering", "structural", "material",
        "construction method", "geotechnical", "hydrological", "topograph",
        "quality control", "standard", "alignment", "capacity", "infrastructure",
        "equipment",
    ],
}

# Compiled once: category -> list of (keyword, compiled regex) for whole-
# phrase, case-insensitive matching against heading text.
_COMPILED: dict[SectionCategory, list[tuple[str, re.Pattern]]] = {
    category: [(kw, re.compile(re.escape(kw), re.IGNORECASE)) for kw in kws]
    for category, kws in _CATEGORY_KEYWORDS.items()
}


def classify_heading(heading_text: str) -> tuple[SectionCategory, float]:
    """Return (category, confidence) where confidence is a rough 0-1 score
    based on keyword specificity (longer/more distinctive matches score
    higher) so callers can decide whether to trust a weak match."""
    best_category = SectionCategory.OTHER
    best_score = 0.0

    for category, patterns in _COMPILED.items():
        for keyword, pattern in patterns:
            if pattern.search(heading_text):
                # Longer keyword matches are more specific/confident, and we
                # normalize against heading length so a keyword that makes
                # up most of a short heading scores higher than the same
                # keyword buried in a long heading.
                score = min(1.0, len(keyword) / max(len(heading_text), len(keyword)))
                score = max(score, 0.55)  # any direct keyword hit is a decent signal
                if score > best_score:
                    best_score = score
                    best_category = category

    return best_category, best_score

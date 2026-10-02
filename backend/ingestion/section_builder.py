"""
Walks the flattened line list and the detected/classified headings to
build contiguous Section objects — the final structured output of the
ingestion phase that the ML feature builder and RAG chunker consume.

Single responsibility: (lines, headings) -> list[Section]. Doesn't touch
PDFs, fonts, or OCR directly.
"""

from __future__ import annotations

from .models import Heading, Section, SectionCategory, TextLine
from .section_classifier import classify_heading

# Minimum keyword-match confidence for a heading to be treated as a
# section-splitting boundary. Headings below this (structural but
# unclassifiable, e.g. "a.", "Table 3") are folded into the enclosing
# section's body text instead of fragmenting the document.
SPLIT_CONFIDENCE_THRESHOLD = 0.55


def _classified_headings(headings: list[Heading]) -> list[tuple[Heading, SectionCategory, float]]:
    out = []
    for h in headings:
        category, confidence = classify_heading(h.text)
        out.append((h, category, confidence))
    return out


def build_sections(lines: list[TextLine], headings: list[Heading]) -> list[Section]:
    classified = _classified_headings(headings)
    splitting = [
        (h, cat, conf) for h, cat, conf in classified
        if cat != SectionCategory.OTHER and conf >= SPLIT_CONFIDENCE_THRESHOLD
    ]

    sections: list[Section] = []

    if not splitting:
        # No recognizable DPR-vocabulary headings at all (e.g. a template
        # or a document following an unfamiliar structure). Emit the
        # whole document as a single OTHER section rather than dropping
        # content — downstream stages still need something to work with.
        full_text = "\n".join(line.text for line in lines)
        if full_text.strip():
            sections.append(
                Section(
                    heading_text="(unclassified document)",
                    category=SectionCategory.OTHER,
                    page_start=lines[0].page_number if lines else 0,
                    page_end=lines[-1].page_number if lines else 0,
                    text=full_text,
                )
            )
        return sections

    # Leading content before the first splitting heading (title page,
    # cover sheet, table of contents) — keep it, tagged OTHER.
    first_idx = splitting[0][0].line_index
    if first_idx > 0:
        lead_lines = lines[:first_idx]
        lead_text = "\n".join(l.text for l in lead_lines).strip()
        if lead_text:
            sections.append(
                Section(
                    heading_text="(front matter)",
                    category=SectionCategory.OTHER,
                    page_start=lead_lines[0].page_number,
                    page_end=lead_lines[-1].page_number,
                    text=lead_text,
                )
            )

    for i, (heading, category, _confidence) in enumerate(splitting):
        start_idx = heading.line_index + 1
        end_idx = splitting[i + 1][0].line_index if i + 1 < len(splitting) else len(lines)
        body_lines = lines[start_idx:end_idx]
        body_text = "\n".join(l.text for l in body_lines).strip()

        page_start = heading.page_number
        page_end = body_lines[-1].page_number if body_lines else heading.page_number

        sections.append(
            Section(
                heading_text=heading.text,
                category=category,
                page_start=page_start,
                page_end=page_end,
                text=body_text,
            )
        )

    return sections

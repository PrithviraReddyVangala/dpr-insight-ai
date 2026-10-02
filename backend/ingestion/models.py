"""
Data models shared across the ingestion pipeline.

These are intentionally plain dataclasses (not ORM/pydantic models) so that
the ingestion package has zero framework dependencies and can be reused
as-is by the ML pipeline, the RAG pipeline, and the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SectionCategory(str, Enum):
    """Canonical DPR sub-section categories used downstream by the ML
    feature builder and the RAG chunk tagger."""

    FINANCIALS = "financials"
    TIMELINE = "timeline"
    SCOPE = "scope"
    CLEARANCES = "clearances"
    TECHNICAL = "technical"
    OTHER = "other"


@dataclass
class TextLine:
    """A single visually-coherent line of text extracted from a PDF page,
    carrying the font metadata needed for heading detection."""

    page_number: int          # 0-indexed
    text: str
    font_size: float
    is_bold: bool
    y_position: float         # top-of-line y coordinate, for reading order
    x_position: float
    is_ocr: bool = False      # True if this line came from the OCR fallback


@dataclass
class Heading:
    """A detected heading candidate, prior to category classification."""

    text: str
    page_number: int
    font_size: float
    is_bold: bool
    y_position: float
    level: int                # 1 = largest/most prominent in the doc, increasing = smaller
    line_index: int            # index into the flattened line list, for slicing sections


@dataclass
class Section:
    """A contiguous span of document content grouped under one heading."""

    heading_text: str
    category: SectionCategory
    page_start: int
    page_end: int
    text: str
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class PageDiagnostics:
    page_number: int
    char_count: int
    is_scanned: bool
    ocr_applied: bool


@dataclass
class ExtractedDocument:
    """The full output of Phase 1 for a single PDF: structured sections
    plus diagnostics, ready to be consumed by the ML and RAG pipelines."""

    source_path: str
    filename: str
    page_count: int
    body_font_size: float
    sections: list[Section]
    page_diagnostics: list[PageDiagnostics]
    scanned_page_count: int
    extraction_warnings: list[str] = field(default_factory=list)

    def sections_by_category(self, category: SectionCategory) -> list[Section]:
        return [s for s in self.sections if s.category == category]

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "filename": self.filename,
            "page_count": self.page_count,
            "body_font_size": self.body_font_size,
            "scanned_page_count": self.scanned_page_count,
            "extraction_warnings": self.extraction_warnings,
            "sections": [
                {
                    "heading_text": s.heading_text,
                    "category": s.category.value,
                    "page_start": s.page_start,
                    "page_end": s.page_end,
                    "char_count": s.char_count,
                    "text": s.text,
                }
                for s in self.sections
            ],
            "page_diagnostics": [
                {
                    "page_number": p.page_number,
                    "char_count": p.char_count,
                    "is_scanned": p.is_scanned,
                    "ocr_applied": p.ocr_applied,
                }
                for p in self.page_diagnostics
            ],
        }

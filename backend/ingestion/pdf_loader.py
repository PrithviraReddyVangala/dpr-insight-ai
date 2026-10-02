"""
PDF loading: turns a PDF file into a flat, page-ordered list of TextLine
objects carrying font metadata, plus per-page diagnostics that flag pages
with no usable text layer (i.e. scanned/image pages needing OCR).

Single responsibility: PDF -> raw text lines with metadata. No heading
logic, no classification, no section building lives here.
"""

from __future__ import annotations

import logging

import pymupdf

from .models import PageDiagnostics, TextLine

logger = logging.getLogger(__name__)

# A page with fewer than this many extracted characters is treated as
# "no usable text layer" and flagged for OCR fallback in a later stage.
SCANNED_PAGE_CHAR_THRESHOLD = 20

# PyMuPDF span flag bit for bold text (see PyMuPDF docs: flags & 2**4)
_BOLD_FLAG_BIT = 1 << 4


def _span_is_bold(span: dict) -> bool:
    if span["flags"] & _BOLD_FLAG_BIT:
        return True

    # Many DPR PDFs use a "-Bold" font variant without setting the flag bit
    font_name = span.get("font", "").lower()
    return "bold" in font_name


def load_pdf_lines(
    pdf_path: str,
) -> tuple[list[TextLine], list[PageDiagnostics], int]:
    """Extract all text lines from a PDF's native text layer.

    Returns:
        lines: flat list of TextLine, in reading order (page, then
            top-to-bottom)
        diagnostics: per-page char counts and scanned-page flags
        page_count: total number of pages in the document
    """
    doc = pymupdf.open(pdf_path)
    lines: list[TextLine] = []
    diagnostics: list[PageDiagnostics] = []

    try:
        for page_index, page in enumerate(doc):
            page_dict = page.get_text("dict")
            page_char_count = 0

            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    # 0 = text block, 1 = image block
                    continue

                for line in block.get("lines", []):
                    spans = line.get("spans", [])

                    if not spans:
                        continue

                    line_text = (
                        "".join(s["text"] for s in spans)
                        .replace("\xa0", " ")
                        .strip()
                    )

                    if not line_text:
                        continue

                    # A line can mix sizes/weights across spans
                    # (e.g. a bold numeral prefix + normal text).
                    # We take the dominant (longest-text) span's
                    # metadata as representative.
                    #
                    # We also flag the line bold if ANY span in it
                    # is bold, since partial-bold lines are still
                    # usually heading fragments.
                    dominant_span = max(
                        spans,
                        key=lambda s: len(s["text"]),
                    )

                    any_bold = any(
                        _span_is_bold(s)
                        for s in spans
                    )

                    bbox = line.get("bbox", [0, 0, 0, 0])

                    lines.append(
                        TextLine(
                            page_number=page_index,
                            text=line_text,
                            font_size=round(
                                dominant_span["size"],
                                1,
                            ),
                            is_bold=any_bold,
                            y_position=bbox[1],
                            x_position=bbox[0],
                            is_ocr=False,
                        )
                    )

                    page_char_count += len(line_text)

            diagnostics.append(
                PageDiagnostics(
                    page_number=page_index,
                    char_count=page_char_count,
                    is_scanned=(
                        page_char_count
                        < SCANNED_PAGE_CHAR_THRESHOLD
                    ),
                    ocr_applied=False,
                )
            )

        page_count = doc.page_count

    finally:
        doc.close()

    return lines, diagnostics, page_count
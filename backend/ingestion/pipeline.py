"""
Phase 1 entry point: orchestrates the full ingestion pipeline for a single
PDF — load -> OCR fallback for scanned pages -> heading detection ->
classification -> section building -> ExtractedDocument.

This is the only module downstream phases (ML feature builder, RAG
chunker, API layer) should import from directly.
"""

from __future__ import annotations

import logging
import os

from .heading_detector import compute_body_font_size, detect_headings
from .models import ExtractedDocument, PageDiagnostics, TextLine
from .ocr_fallback import ocr_page
from .pdf_loader import load_pdf_lines
from .section_builder import build_sections

logger = logging.getLogger(__name__)

# If more than this fraction of pages are scanned, OCR-ing every one of
# them can be slow; we still do it (correctness over speed for a DPR
# compliance tool) but we surface a warning so the caller/UI can show
# a "this document required heavy OCR" notice.
HEAVY_OCR_WARNING_RATIO = 0.5


def extract_document(
    pdf_path: str,
    max_ocr_pages: int | None = None,
    progress_callback=None,
) -> ExtractedDocument:
    """
    max_ocr_pages: if set, caps how many scanned pages get OCR'd (the
    remainder are left with empty text but still counted in
    scanned_page_count/diagnostics). Full-fidelity single-document
    extraction (the real product path) should leave this as None. This
    exists for bounded-time batch corpus building over many large,
    fully-scanned PDFs — it's disclosed here rather than silently capping.

    progress_callback: optional callable(stage: str, current: int, total: int,
    message: str) invoked at each meaningful step (native load done, each
    OCR page, section building done) so a caller (e.g. the API layer) can
    surface live progress instead of a blind spinner.
    """
    def _report(stage: str, current: int, total: int, message: str) -> None:
        if progress_callback:
            progress_callback(stage, current, total, message)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)

    _report("loading", 0, 1, "Reading PDF and extracting native text layer")
    lines, diagnostics, page_count = load_pdf_lines(pdf_path)
    warnings: list[str] = []
    _report("loading", 1, 1, f"Loaded {page_count} pages")

    scanned_pages = [d.page_number for d in diagnostics if d.is_scanned]
    if max_ocr_pages is not None and len(scanned_pages) > max_ocr_pages:
        warnings.append(
            f"OCR capped at {max_ocr_pages}/{len(scanned_pages)} scanned pages for this run."
        )
        scanned_pages = scanned_pages[:max_ocr_pages]
    if scanned_pages:
        logger.info("OCR fallback needed for %d/%d pages of %s",
                     len(scanned_pages), page_count, pdf_path)
        ocr_lines: list[TextLine] = []
        for i, page_num in enumerate(scanned_pages):
            _report("ocr", i, len(scanned_pages), f"Running OCR on page {page_num + 1}")
            try:
                page_ocr_lines = ocr_page(pdf_path, page_num)
                ocr_lines.extend(page_ocr_lines)
                diagnostics[page_num] = PageDiagnostics(
                    page_number=page_num,
                    char_count=sum(len(l.text) for l in page_ocr_lines),
                    is_scanned=True,
                    ocr_applied=True,
                )
            except Exception as exc:  # OCR failures shouldn't kill the whole doc
                warnings.append(f"OCR failed on page {page_num + 1}: {exc}")
                logger.warning("OCR failed on page %d of %s: %s", page_num, pdf_path, exc)
        _report("ocr", len(scanned_pages), len(scanned_pages), "OCR complete")

        # Merge OCR'd lines back in page order, replacing native lines for
        # those pages (which had ~0 usable characters anyway).
        native_by_page: dict[int, list[TextLine]] = {}
        for line in lines:
            native_by_page.setdefault(line.page_number, []).append(line)
        for page_num in scanned_pages:
            native_by_page[page_num] = [l for l in ocr_lines if l.page_number == page_num]

        lines = [line for page_num in sorted(native_by_page) for line in native_by_page[page_num]]

        if len(scanned_pages) / max(page_count, 1) > HEAVY_OCR_WARNING_RATIO:
            warnings.append(
                f"{len(scanned_pages)} of {page_count} pages had no native text layer "
                "and required OCR — extraction quality on those pages may be lower."
            )

    _report("structuring", 0, 1, "Detecting headings and classifying sections")
    body_size = compute_body_font_size(lines)
    headings = detect_headings(lines, body_size)
    sections = build_sections(lines, headings)
    _report("structuring", 1, 1, f"Found {len(sections)} sections")

    if not sections:
        warnings.append("No text content could be extracted from this document.")

    return ExtractedDocument(
        source_path=pdf_path,
        filename=os.path.basename(pdf_path),
        page_count=page_count,
        body_font_size=body_size,
        sections=sections,
        page_diagnostics=diagnostics,
        scanned_page_count=len(scanned_pages),
        extraction_warnings=warnings,
    )

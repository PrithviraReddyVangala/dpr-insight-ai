"""
OCR fallback for pages with no usable native text layer (scanned DPRs are
common — site photos, signed clearance letters, scanned annexures).

Single responsibility: rasterize a flagged page and run Tesseract on it,
returning TextLine objects in the same shape the native loader produces so
downstream code never has to know which path a page came from.
"""

from __future__ import annotations

import logging

import pymupdf
import pytesseract
from PIL import Image

from .models import TextLine

logger = logging.getLogger(__name__)

# Render at this DPI before OCR — Tesseract accuracy drops sharply below
# ~200 DPI on scanned government documents (small print, tables, stamps).
OCR_RENDER_DPI = 300


def ocr_page(pdf_path: str, page_number: int) -> list[TextLine]:
    """Run OCR on a single page and return its text as one or more
    TextLine objects.

    The page is rendered at OCR_RENDER_DPI and processed using Tesseract.
    Tesseract's block, paragraph, and line information is preserved so
    downstream processing receives the same TextLine structure used by
    native PDF extraction.
    """
    doc = pymupdf.open(pdf_path)

    try:
        page = doc[page_number]

        zoom = OCR_RENDER_DPI / 72  # PDF base unit is 72 DPI

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(zoom, zoom)
        )

        img = Image.frombytes(
            "RGB",
            (pix.width, pix.height),
            pix.samples,
        )

    finally:
        doc.close()

    ocr_data = pytesseract.image_to_data(
        img,
        output_type=pytesseract.Output.DICT,
    )

    lines: list[TextLine] = []

    current_line_key = None
    current_words: list[str] = []
    current_top = 0.0
    current_left = 0.0

    n = len(ocr_data["text"])

    for i in range(n):
        word = ocr_data["text"][i].strip()

        if not word:
            continue

        # block_num/par_num/line_num together identify a visual line.
        line_key = (
            ocr_data["block_num"][i],
            ocr_data["par_num"][i],
            ocr_data["line_num"][i],
        )

        if line_key != current_line_key:

            # Save the previous OCR line.
            if current_words:
                lines.append(
                    TextLine(
                        page_number=page_number,
                        text=" ".join(current_words),
                        font_size=10.0,
                        is_bold=False,
                        y_position=current_top / zoom,
                        x_position=current_left / zoom,
                        is_ocr=True,
                    )
                )

            current_words = []
            current_line_key = line_key

            current_top = ocr_data["top"][i]
            current_left = ocr_data["left"][i]

        current_words.append(word)

    # Save the final OCR line.
    if current_words:
        lines.append(
            TextLine(
                page_number=page_number,
                text=" ".join(current_words),
                font_size=10.0,
                is_bold=False,
                y_position=current_top / zoom,
                x_position=current_left / zoom,
                is_ocr=True,
            )
        )

    return lines
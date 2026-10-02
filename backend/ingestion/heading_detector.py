"""
Heading detection: turns a flat list of TextLine into a list of Heading
candidates, using font size relative to the document's body text size,
bold weighting, and numbered-heading patterns (e.g. "1.1", "Chapter 2:").

Single responsibility: identify WHERE the headings are and their relative
prominence (level). Classifying WHAT each heading means (Financials vs
Timeline etc.) is section_classifier.py's job, kept separate so the
detection heuristic can be reused for section types beyond the five
canonical DPR categories.
"""

from __future__ import annotations

import re
from collections import Counter

from .models import Heading, TextLine

# A heading candidate's font size must be at least this many times the
# body text size, OR be bold, to qualify.
SIZE_RATIO_THRESHOLD = 1.15

# Headings longer than this are almost always mis-detected body paragraphs
# (e.g. a bold-emphasized sentence), not real section headings.
MAX_HEADING_CHARS = 140

# Vertical gap (in points) within which two consecutive heading-candidate
# lines are considered a single wrapped heading rather than two headings.
WRAP_MERGE_Y_GAP = 18

_NUMBERED_PATTERN = re.compile(
    r"^\s*(chapter\s+\d+|annex(ure)?\s+[a-z0-9]+|section\s+\d+|\d+(\.\d+)*[\.\)]?)\s*[:\-]?\s*",
    re.IGNORECASE,
)


def compute_body_font_size(lines: list[TextLine]) -> float:
    """The body font size is the size carrying the most total characters
    in the document — i.e. whatever font size the bulk of the prose is
    set in, regardless of how many distinct heading sizes exist above it."""
    if not lines:
        return 10.0
    weighted = Counter()
    for line in lines:
        weighted[line.font_size] += len(line.text)
    return weighted.most_common(1)[0][0]


def _is_heading_candidate(line: TextLine, body_size: float) -> bool:
    if len(line.text) > MAX_HEADING_CHARS:
        return False
    if line.text.strip().endswith((".", ",")) and not _NUMBERED_PATTERN.match(line.text):
        # Sentences ending in a period are very rarely headings, unless
        # they're numbered ("1.2." style periods are fine).
        return False
    size_ok = line.font_size >= body_size * SIZE_RATIO_THRESHOLD
    bold_ok = line.is_bold and line.font_size >= body_size * 0.95
    numbered = bool(_NUMBERED_PATTERN.match(line.text))
    return size_ok or (bold_ok and (numbered or len(line.text.split()) <= 12))


def _assign_levels(candidate_sizes: list[float]) -> dict[float, int]:
    """Map each distinct font size present among candidates to a level,
    largest size = level 1."""
    distinct_sorted = sorted(set(candidate_sizes), reverse=True)
    return {size: idx + 1 for idx, size in enumerate(distinct_sorted)}


def detect_headings(lines: list[TextLine], body_size: float) -> list[Heading]:
    candidates: list[tuple[int, TextLine]] = [
        (idx, line) for idx, line in enumerate(lines) if _is_heading_candidate(line, body_size)
    ]
    if not candidates:
        return []

    level_map = _assign_levels([line.font_size for _, line in candidates])

    # Merge consecutive candidate lines that are really one wrapped heading:
    # same page, same font size/bold, small vertical gap, adjacent indices.
    merged: list[Heading] = []
    i = 0
    while i < len(candidates):
        idx, line = candidates[i]
        text_parts = [line.text]
        j = i + 1
        while j < len(candidates):
            next_idx, next_line = candidates[j]
            same_run = (
                next_idx == idx + (j - i)  # contiguous in the line list
                and next_line.page_number == line.page_number
                and next_line.font_size == line.font_size
                and next_line.is_bold == line.is_bold
                and (next_line.y_position - line.y_position) < WRAP_MERGE_Y_GAP * (j - i)
            )
            if not same_run:
                break
            text_parts.append(next_line.text)
            j += 1

        merged.append(
            Heading(
                text=" ".join(text_parts).strip(),
                page_number=line.page_number,
                font_size=line.font_size,
                is_bold=line.is_bold,
                y_position=line.y_position,
                level=level_map[line.font_size],
                line_index=idx,
            )
        )
        i = j

    return merged

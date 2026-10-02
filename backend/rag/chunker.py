"""
Chunking: turns Phase 1 Sections into overlapping text chunks sized for
embedding + retrieval, carrying metadata (source file, category, heading,
page range) so RAG answers can cite where content came from.

Single responsibility: Section -> list[Chunk]. No embedding, no indexing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingestion.models import ExtractedDocument, Section, SectionCategory

# Target chunk size in characters. Sentence-transformers MiniLM has a
# 256-token effective context; ~800 chars keeps most chunks under that
# after tokenization while staying large enough to carry real context.
TARGET_CHUNK_CHARS = 800
CHUNK_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 80  # discard trailing fragments shorter than this

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_file: str
    category: SectionCategory
    heading_text: str
    page_start: int
    page_end: int


def _split_into_chunks(text: str) -> list[str]:
    """Greedy sentence-aware chunking: accumulate sentences until we hit
    the target size, then start a new chunk seeded with the overlap tail
    of the previous one so retrieval doesn't lose context at boundaries."""
    sentences = _SENTENCE_SPLIT.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return []

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > TARGET_CHUNK_CHARS and current:
            chunks.append(current)
            # seed next chunk with the tail of the current one for overlap
            tail = current[-CHUNK_OVERLAP_CHARS:]
            current = f"{tail} {sentence}".strip()
        else:
            current = candidate

    if current and len(current) >= MIN_CHUNK_CHARS:
        chunks.append(current)
    elif current and chunks:
        # fold a too-short trailing fragment into the previous chunk
        chunks[-1] = f"{chunks[-1]} {current}".strip()

    return chunks


def chunk_section(doc: ExtractedDocument, section: Section, section_index: int) -> list[Chunk]:
    pieces = _split_into_chunks(section.text)
    return [
        Chunk(
            chunk_id=f"{doc.filename}::s{section_index}::c{i}",
            text=piece,
            source_file=doc.filename,
            category=section.category,
            heading_text=section.heading_text,
            page_start=section.page_start,
            page_end=section.page_end,
        )
        for i, piece in enumerate(pieces)
    ]


def chunk_document(doc: ExtractedDocument) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, section in enumerate(doc.sections):
        chunks.extend(chunk_section(doc, section, i))
    return chunks

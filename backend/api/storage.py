"""
Lightweight persistence for uploaded documents: status, progress, and
cached analysis results (risk assessment, section summary). SQLite via
the standard library — no ORM, no external DB server, since this is a
single-process personal-project deployment and the schema is small.

Single responsibility: document metadata CRUD. No extraction/ML/RAG logic.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "documents.db"
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    status TEXT NOT NULL,               -- uploaded | extracting | analyzing | indexing | ready | failed
    progress_stage TEXT,
    progress_pct REAL DEFAULT 0,
    progress_message TEXT,
    error_message TEXT,
    page_count INTEGER,
    scanned_page_count INTEGER,
    section_count INTEGER,
    risk_score REAL,
    risk_bucket TEXT,
    extraction_warnings TEXT,           -- JSON array
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(SCHEMA)


@dataclass
class DocumentRecord:
    id: str
    original_filename: str
    stored_path: str
    status: str
    progress_stage: str | None = None
    progress_pct: float = 0.0
    progress_message: str | None = None
    error_message: str | None = None
    page_count: int | None = None
    scanned_page_count: int | None = None
    section_count: int | None = None
    risk_score: float | None = None
    risk_bucket: str | None = None
    extraction_warnings: list = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "DocumentRecord":
        d = dict(row)
        d["extraction_warnings"] = json.loads(d["extraction_warnings"] or "[]")
        return cls(**d)


def create_document(original_filename: str, stored_path: str) -> DocumentRecord:
    doc_id = str(uuid.uuid4())
    now = time.time()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO documents
               (id, original_filename, stored_path, status, progress_stage,
                progress_pct, extraction_warnings, created_at, updated_at)
               VALUES (?, ?, ?, 'uploaded', 'uploaded', 0, '[]', ?, ?)""",
            (doc_id, original_filename, stored_path, now, now),
        )
    return get_document(doc_id)


def update_progress(doc_id: str, status: str, stage: str, pct: float, message: str) -> None:
    with _connect() as conn:
        conn.execute(
            """UPDATE documents SET status=?, progress_stage=?, progress_pct=?,
               progress_message=?, updated_at=? WHERE id=?""",
            (status, stage, pct, message, time.time(), doc_id),
        )


def mark_failed(doc_id: str, error_message: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE documents SET status='failed', error_message=?, updated_at=? WHERE id=?",
            (error_message, time.time(), doc_id),
        )


def mark_ready(
    doc_id: str,
    page_count: int,
    scanned_page_count: int,
    section_count: int,
    risk_score: float,
    risk_bucket: str,
    extraction_warnings: list[str],
) -> None:
    with _connect() as conn:
        conn.execute(
            """UPDATE documents SET status='ready', progress_stage='done', progress_pct=100,
               progress_message='Analysis complete', page_count=?, scanned_page_count=?,
               section_count=?, risk_score=?, risk_bucket=?, extraction_warnings=?, updated_at=?
               WHERE id=?""",
            (page_count, scanned_page_count, section_count, risk_score, risk_bucket,
             json.dumps(extraction_warnings), time.time(), doc_id),
        )


def get_document(doc_id: str) -> DocumentRecord | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        return DocumentRecord.from_row(row) if row else None


def list_documents() -> list[DocumentRecord]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [DocumentRecord.from_row(r) for r in rows]


def delete_document(doc_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))


init_db()

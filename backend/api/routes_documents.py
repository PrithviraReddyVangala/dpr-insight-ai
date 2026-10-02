"""
Document lifecycle endpoints: upload (kicks off the async background
pipeline), list, status polling, detail retrieval, delete.

Single responsibility: HTTP concerns for documents. Pipeline logic lives
in api/jobs.py; persistence in api/storage.py.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api import jobs, storage
from api.schemas import DocumentDetail, DocumentSummary, SectionOut, UploadResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200MB — largest file in the sample corpus was ~120MB


def _to_summary(record: storage.DocumentRecord) -> DocumentSummary:
    return DocumentSummary(**vars(record))


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    stored_name = f"{uuid.uuid4()}.pdf"
    stored_path = storage.UPLOAD_DIR / stored_name

    size = 0
    with open(stored_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(413, "File exceeds 200MB limit.")
            out.write(chunk)

    record = storage.create_document(file.filename, str(stored_path))
    jobs.submit_extraction_job(record.id, str(stored_path))

    return UploadResponse(id=record.id, status="uploaded", message="Extraction started")


@router.get("", response_model=list[DocumentSummary])
def list_documents():
    return [_to_summary(r) for r in storage.list_documents()]


@router.get("/{doc_id}/status", response_model=DocumentSummary)
def get_status(doc_id: str):
    record = storage.get_document(doc_id)
    if not record:
        raise HTTPException(404, "Document not found")
    return _to_summary(record)


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document_detail(doc_id: str):
    record = storage.get_document(doc_id)
    if not record:
        raise HTTPException(404, "Document not found")
    if record.status != "ready":
        raise HTTPException(409, f"Document is not ready yet (status={record.status})")

    extracted = jobs.load_extracted_document(doc_id)
    if extracted is None:
        raise HTTPException(500, "Document marked ready but extraction cache is missing")

    sections = [SectionOut(**s) for s in extracted["sections"]]
    return DocumentDetail(**vars(record), sections=sections)


@router.get("/{doc_id}/file")
def get_document_file(doc_id: str):
    record = storage.get_document(doc_id)
    if not record:
        raise HTTPException(404, "Document not found")
    path = Path(record.stored_path)
    if not path.exists():
        raise HTTPException(404, "Stored file is missing")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=record.original_filename,
        headers={"Content-Disposition": f'inline; filename="{record.original_filename}"'},
    )


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    record = storage.get_document(doc_id)
    if not record:
        raise HTTPException(404, "Document not found")

    Path(record.stored_path).unlink(missing_ok=True)
    (jobs.EXTRACTED_CACHE_DIR / f"{doc_id}.json").unlink(missing_ok=True)
    (jobs.RAG_INDEX_DIR / f"{doc_id}.faiss").unlink(missing_ok=True)
    (jobs.RAG_INDEX_DIR / f"{doc_id}.jsonl").unlink(missing_ok=True)
    storage.delete_document(doc_id)
    return {"deleted": doc_id}

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from uuid import uuid4
from .dependencies import case_key
from ..core.security import current_user
from ..db import connection
from ..infrastructure.jobs import enqueue_ingestion
from ..infrastructure.parsing import DocumentParseError, validate_upload
from ..services import audit

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])

@router.post("")
async def upload(case_id: str, file: UploadFile = File(...), user=Depends(current_user)):
    case_key(case_id, user["id"])
    raw = await file.read(); filename = file.filename or "upload"
    try: validate_upload(filename, raw)
    except DocumentParseError as exc: raise HTTPException(400, str(exc))
    document_id = str(uuid4())
    with connection() as conn: conn.execute("INSERT INTO documents VALUES (?,?,?,?,?,?)", (document_id, case_id, filename, "", "queued", 0))
    enqueue_ingestion(case_id, document_id, filename, raw)
    audit(user["id"], case_id, "document_uploaded", {"document_id": document_id})
    return {"id": document_id, "status": "queued"}

@router.get("")
def documents(case_id: str, user=Depends(current_user)):
    case_key(case_id, user["id"])
    with connection() as conn: rows = conn.execute("SELECT id,filename,status,page_count FROM documents WHERE case_id=?", (case_id,)).fetchall()
    audit(user["id"], case_id, "documents_listed")
    return [dict(row) for row in rows]

@router.get("/{document_id}/page/{page}")
def source_page(case_id: str, document_id: str, page: int, user=Depends(current_user)):
    key = case_key(case_id, user["id"])
    from ..core.crypto import decrypt
    with connection() as conn: rows = conn.execute("SELECT paragraph,text FROM chunks WHERE case_id=? AND document_id=? AND page=? ORDER BY paragraph", (case_id, document_id, page)).fetchall()
    if not rows: raise HTTPException(404, "Source page not found")
    audit(user["id"], case_id, "source_viewed", {"document_id": document_id, "page": page})
    return {"case_id": case_id, "document_id": document_id, "page": page, "paragraphs": [{"paragraph": row["paragraph"], "text": decrypt(row["text"], key).decode()} for row in rows]}

import json
from fastapi import APIRouter, Depends
from uuid import uuid4
from .dependencies import case_key
from ..core.crypto import decrypt, encrypt
from ..core.security import current_user
from ..db import connection
from ..schemas.queries import QueryRequest
from ..services import audit, grounded_answer
from ..services.retrieval import hybrid_retrieve

router = APIRouter(prefix="/cases/{case_id}", tags=["queries"])

@router.post("/query")
def query(case_id: str, data: QueryRequest, user=Depends(current_user)):
    key = case_key(case_id, user["id"]); matches = hybrid_retrieve(case_id, data.question, key); answer, citations = grounded_answer(data.question, matches)
    with connection() as conn:
        conn.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?,?)", (str(uuid4()), case_id, user["id"], "user", encrypt(data.question.encode(), key), "[]"))
        conn.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?,?)", (str(uuid4()), case_id, user["id"], "assistant", encrypt(answer.encode(), key), json.dumps(citations)))
    audit(user["id"], case_id, "query", {"result_count": len(citations)})
    return {"answer": answer, "citations": citations, "disclaimer": "Retrieved information from your documents, not legal advice."}

@router.get("/key-points")
def key_points(case_id: str, user=Depends(current_user)):
    key = case_key(case_id, user["id"])
    with connection() as conn: rows = conn.execute("SELECT * FROM extractions WHERE case_id=?", (case_id,)).fetchall()
    audit(user["id"], case_id, "key_points_viewed")
    return [{"field_type": row["field_type"], "value": decrypt(row["value"], key).decode(), "document_id": row["document_id"], "page": row["page"], "paragraph": row["paragraph"], "quote": decrypt(row["quote"], key).decode()} for row in rows]

@router.get("/messages")
def messages(case_id: str, user=Depends(current_user)):
    key = case_key(case_id, user["id"])
    with connection() as conn: rows = conn.execute("SELECT role,content,citations FROM chat_messages WHERE case_id=? ORDER BY rowid", (case_id,)).fetchall()
    audit(user["id"], case_id, "chat_history_viewed")
    return [{"role": row["role"], "content": decrypt(row["content"], key).decode(), "citations": json.loads(row["citations"])} for row in rows]

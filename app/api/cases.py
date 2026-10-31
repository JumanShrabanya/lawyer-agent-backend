from fastapi import APIRouter, Depends, HTTPException
from uuid import uuid4
from ..core.crypto import new_case_key, wrap_key
from ..core.security import current_user, require_member
from ..db import connection
from ..services import audit
from ..schemas.cases import CaseCreateRequest

router = APIRouter(prefix="/cases", tags=["cases"])

@router.post("")
def create_case(data: CaseCreateRequest, user=Depends(current_user)):
    case_id = str(uuid4())
    with connection() as conn:
        conn.execute("INSERT INTO cases VALUES (?,?,?,?,datetime('now'))", (case_id, data.name, user["id"], wrap_key(new_case_key())))
        conn.execute("INSERT INTO case_members VALUES (?,?,?)", (case_id, user["id"], "owner"))
    audit(user["id"], case_id, "case_created")
    return {"id": case_id, "name": data.name}

@router.get("")
def list_cases(user=Depends(current_user)):
    with connection() as conn: rows = conn.execute("SELECT c.id,c.name,c.created_at,m.role FROM cases c JOIN case_members m ON m.case_id=c.id WHERE m.user_id=?", (user["id"],)).fetchall()
    audit(user["id"], None, "cases_listed")
    return [dict(row) for row in rows]

@router.delete("/{case_id}")
def delete_case(case_id: str, user=Depends(current_user)):
    role = require_member(user["id"], case_id)
    if role != "owner": raise HTTPException(403, "Only the owner can delete a case")
    with connection() as conn: conn.execute("DELETE FROM cases WHERE id=?", (case_id,))
    from ..core.config import DATA_DIR
    import shutil
    shutil.rmtree(DATA_DIR / "cases" / case_id, ignore_errors=True)
    audit(user["id"], case_id, "case_deleted")
    return {"deleted": True}

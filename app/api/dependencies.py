from fastapi import HTTPException
from ..core.crypto import unwrap_key
from ..core.security import require_member
from ..db import connection

def case_key(case_id: str, user_id: str):
    require_member(user_id, case_id)
    with connection() as conn:
        row = conn.execute("SELECT encrypted_data_key FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row: raise HTTPException(404, "Case not found")
    return unwrap_key(row["encrypted_data_key"])

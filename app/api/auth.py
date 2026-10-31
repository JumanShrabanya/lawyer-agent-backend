from fastapi import APIRouter, HTTPException, Request
from uuid import uuid4
from ..core.security import hash_password, verify_password, create_token, rate_limit
from ..db import connection
from ..schemas.auth import LoginRequest

router = APIRouter(tags=["auth"])

@router.post("/auth/register")
def register(data: LoginRequest, request: Request):
    rate_limit(request, "register", 10)
    uid = str(uuid4())
    with connection() as conn:
        try: conn.execute("INSERT INTO users VALUES (?,?,?,NULL)", (uid, data.email.lower(), hash_password(data.password)))
        except Exception: raise HTTPException(409, "Email already registered")
    return {"access_token": create_token(uid), "token_type": "bearer"}

@router.post("/auth/login")
def login(data: LoginRequest, request: Request):
    rate_limit(request, "login", 20)
    with connection() as conn: user = conn.execute("SELECT * FROM users WHERE email=?", (data.email.lower(),)).fetchone()
    if not user or not verify_password(data.password, user["password_hash"]): raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_token(user["id"]), "token_type": "bearer"}

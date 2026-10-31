from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request
from time import monotonic
from .config import APP_SECRET, ACCESS_TOKEN_MINUTES
from ..db import connection

_requests = {}
def rate_limit(request: Request, bucket: str, max_requests: int = 60, window: int = 60):
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"
    now = monotonic(); recent = [stamp for stamp in _requests.get(key, []) if now - stamp < window]
    if len(recent) >= max_requests: raise HTTPException(429, "Rate limit exceeded")
    recent.append(now); _requests[key] = recent

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(value: str) -> str: return pwd.hash(value)
def verify_password(value: str, hashed: str) -> bool: return pwd.verify(value, hashed)
def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}, APP_SECRET, algorithm="HS256")
def current_user(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "): raise HTTPException(401, "Authentication required")
    try: payload = jwt.decode(auth[7:], APP_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired session")
    with connection() as conn: user = conn.execute("SELECT id,email FROM users WHERE id=?", (payload["sub"],)).fetchone()
    if not user: raise HTTPException(401, "Invalid session")
    return user

def require_member(user_id: str, case_id: str):
    with connection() as conn:
        row = conn.execute("SELECT role FROM case_members WHERE case_id=? AND user_id=?", (case_id, user_id)).fetchone()
    if not row: raise HTTPException(403, "Case access denied")
    return row["role"]

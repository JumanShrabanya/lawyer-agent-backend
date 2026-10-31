import sqlite3
from contextlib import contextmanager
from ..core.config import DATABASE_PATH

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, mfa_secret TEXT);
CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_by TEXT NOT NULL, encrypted_data_key BLOB NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(created_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS case_members (case_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY(case_id,user_id), FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, filename TEXT NOT NULL, storage_key TEXT NOT NULL, status TEXT NOT NULL, page_count INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, document_id TEXT NOT NULL, page INTEGER NOT NULL, paragraph INTEGER NOT NULL, text BLOB NOT NULL, embedding TEXT NOT NULL DEFAULT '[]', FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE, FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS extractions (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, field_type TEXT NOT NULL, value BLOB NOT NULL, document_id TEXT NOT NULL, page INTEGER NOT NULL, paragraph INTEGER NOT NULL, quote BLOB NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS audit_log (id TEXT PRIMARY KEY, user_id TEXT, case_id TEXT, action TEXT NOT NULL, timestamp TEXT NOT NULL, metadata TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_messages (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL, content BLOB NOT NULL, citations TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);
"""

@contextmanager
def connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(chunks)")}
        if "embedding" not in columns:
            conn.execute("ALTER TABLE chunks ADD COLUMN embedding TEXT NOT NULL DEFAULT '[]'")

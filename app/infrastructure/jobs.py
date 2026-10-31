from concurrent.futures import ThreadPoolExecutor
from ..db import connection
from ..core.crypto import unwrap_key
from ..services import ingest

executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="case-ingest")

def _run(case_id: str, document_id: str, filename: str, raw: bytes, wrapped_key: bytes):
    try:
        ingest(case_id, document_id, filename, raw, unwrap_key(wrapped_key))
    except Exception:
        with connection() as conn:
            conn.execute("UPDATE documents SET status='failed' WHERE id=?", (document_id,))

def enqueue_ingestion(case_id: str, document_id: str, filename: str, raw: bytes):
    with connection() as conn:
        row = conn.execute("SELECT encrypted_data_key FROM cases WHERE id=?", (case_id,)).fetchone()
    executor.submit(_run, case_id, document_id, filename, raw, row["encrypted_data_key"])

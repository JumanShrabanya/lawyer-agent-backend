# Confidential Legal Case Assistant backend

Local development backend for the per-case, extractive legal document assistant.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:APP_SECRET = 'a-long-development-secret'
uvicorn app.main:app --reload
```

The development backend uses SQLite and deterministic local retrieval. It does not call an external model or logging service. PostgreSQL/pgvector, OCR, and self-hosted embedding/LLM providers can be added behind the service interfaces without changing the case authorization boundary.

## Structure

- `app/api/` — HTTP routers and request dependencies
- `app/schemas/` — validated API request models
- `app/core/` — configuration, authentication, encryption, rate limiting
- `app/db/` — database connection and schema initialization
- `app/services/` — case processing, extraction, retrieval, grounding
- `app/infrastructure/` — parsing, OCR boundary, and background ingestion jobs
- `tests/` — backend security and behavior tests

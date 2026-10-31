from fastapi import FastAPI
from .db import init_db
from .api import auth, cases, documents, queries

app = FastAPI(title="Confidential Legal Case Assistant", version="0.1.0")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "outbound_inference": False}

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(queries.router)

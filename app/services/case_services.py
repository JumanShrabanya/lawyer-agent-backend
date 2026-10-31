import json, re
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from ..core.config import DATA_DIR
from ..core.crypto import encrypt, decrypt
from ..db import connection
from ..infrastructure.parsing import parse_document
from .retrieval import embedding_provider

NO_RESULT = "No relevant information found in this case's documents."
REFUSAL = "This tool only retrieves and extracts information from the case documents; it cannot provide legal advice, opinions, predictions, or strategy."
STOP = {"the","and","for","with","that","this","from","what","where","when","does","have","about"}
FIELD_PATTERNS = {
    "parties_roles": re.compile(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4})\s+(?:is|,?\s+the)\s+(plaintiff|defendant|petitioner|respondent|appellant|appellee)\b", re.I),
    "timeline": re.compile(r"\b(?:on\s+)?((?:\d{1,2}[/-])?\d{1,2}[/-]\d{2,4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b", re.I),
    "monetary_amount": re.compile(r"(?:[$₹€£]\s?[\d,]+(?:\.\d{1,2})?|(?:USD|INR|EUR|GBP)\s+[\d,]+(?:\.\d{1,2})?)", re.I),
    "statute_or_section": re.compile(r"\b(?:Section|Sec\.?|Article)\s+[\w().-]+(?:\s+of\s+the\s+[A-Z][A-Za-z ]+)?", re.I),
    "precedent": re.compile(r"\b[A-Z][A-Za-z]+\s+v\.?\s+[A-Z][A-Za-z]+(?:\s*\[[^\]]+\]|\s*\([^)]*\))?"),
    "claims_allegations_relief": re.compile(r"\b(?:alleges?|alleged|claims?|claimed|seeks?|sought|relief|prays?|prayer for)\b[^.\n]*", re.I),
    "orders_deadlines_hearings": re.compile(r"\b(?:ordered|order|deadline|hearing|next listed|due on|by order)\b[^.\n]*", re.I),
}

def audit(user_id, case_id, action, metadata=None):
    with connection() as c: c.execute("INSERT INTO audit_log VALUES (?,?,?,?,?,?)", (str(uuid4()),user_id,case_id,action,datetime.now(timezone.utc).isoformat(),json.dumps(metadata or {})))
def tokenize(s): return set(re.findall(r"[a-z0-9]+", s.lower())) - STOP
def retrieve(case_id, query, key, limit=5):
    q = tokenize(query)
    with connection() as c: rows = c.execute("SELECT id,document_id,page,paragraph,text FROM chunks WHERE case_id=?", (case_id,)).fetchall()
    scored = []
    for row in rows:
        text = decrypt(row["text"], key).decode()
        score = len(q & tokenize(text))
        if score: scored.append((score,row,text))
    return [(r,t) for _,r,t in sorted(scored,key=lambda x:x[0],reverse=True)[:limit]]

def grounded_answer(query, matches):
    if any(x in query.lower() for x in ("should i", "should we", "advise", "advice", "likely", "predict", "win", "strategy", "opinion")): return REFUSAL, []
    if not matches: return NO_RESULT, []
    citations=[]; sentences=[]
    for row,text in matches:
        sentence = text.strip().split("\n")[0]
        if sentence and sentence not in sentences:
            sentences.append(sentence); citations.append({"document_id":row["document_id"],"page":row["page"],"paragraph":row["paragraph"],"quote":sentence})
    return " ".join(sentences), citations

def grounded_model_answer(query, candidate, matches):
    """Keep only model sentences supported by retrieved source text."""
    if any(x in query.lower() for x in ("should i", "should we", "advise", "advice", "likely", "predict", "win", "strategy", "opinion")):
        return REFUSAL, []
    source_sentences = []
    for row, text in matches:
        source_sentences.extend(part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip())
    accepted = []
    citations = []
    for sentence in re.split(r"(?<=[.!?])\s+", candidate.strip()):
        sentence = sentence.strip()
        if not sentence: continue
        candidates = [(SequenceMatcher(None, sentence.lower(), source.lower()).ratio(), row, source) for row, text in matches for source in re.split(r"(?<=[.!?])\s+", text) if source.strip()]
        match = max(candidates, default=(0, None, ""))
        if match[0] >= 0.80:
            accepted.append(sentence)
            citations.append({"document_id": match[1]["document_id"], "page": match[1]["page"], "paragraph": match[1]["paragraph"], "quote": match[2].strip()})
    return (" ".join(accepted) or NO_RESULT), citations

def extract_key_points(case_id, document_id, page, paragraph, text, key):
    """Extract only fixed, source-backed fields; never synthesize a summary."""
    found = []
    for field, pattern in FIELD_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if field == "parties_roles": value = f"{match.group(1).strip()} — {match.group(2).lower()}"
            found.append((field, value, text.strip()))
    with connection() as c:
        for field, value, quote in found:
            c.execute("INSERT INTO extractions VALUES (?,?,?,?,?,?,?,?)", (str(uuid4()),case_id,field,encrypt(value.encode(),key),document_id,page,paragraph,encrypt(quote.encode(),key)))
    return len(found)

def ingest(case_id, document_id, filename, raw, key):
    pages = parse_document(filename, raw)
    doc_dir = DATA_DIR / "cases" / case_id; doc_dir.mkdir(parents=True, exist_ok=True)
    storage = doc_dir / f"{document_id}.bin"; storage.write_bytes(encrypt(raw,key))
    paragraphs = []
    with connection() as c:
        c.execute("UPDATE documents SET status='processing',storage_key=?,page_count=? WHERE id=?", (str(storage.relative_to(DATA_DIR)),len(pages),document_id))
        for page_no,page_text in enumerate(pages,1):
            for para_no, para in enumerate([p.strip() for p in re.split(r"\n\s*\n",page_text) if p.strip()],1):
                c.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?)", (str(uuid4()),case_id,document_id,page_no,para_no,encrypt(para.encode(),key),__import__('json').dumps(embedding_provider.embed(para))))
                paragraphs.append((page_no, para_no, para))
        c.execute("UPDATE documents SET status='ready' WHERE id=?", (document_id,))
    for page_no, para_no, para in paragraphs:
        extract_key_points(case_id, document_id, page_no, para_no, para, key)

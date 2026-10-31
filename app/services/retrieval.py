"""Swappable offline embedding and hybrid retrieval primitives."""
import hashlib
import json
import math
import re
from ..core.crypto import decrypt
from ..db import connection

class EmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Offline development provider; replace with a local e5/bge adapter."""
    dimensions = 128

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += 1.0 if digest[2] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

embedding_provider = LocalHashEmbeddingProvider()

def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))

def hybrid_retrieve(case_id: str, query: str, key: bytes, limit: int = 5):
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    query_vector = embedding_provider.embed(query)
    with connection() as conn:
        rows = conn.execute("SELECT id,document_id,page,paragraph,text,embedding FROM chunks WHERE case_id=?", (case_id,)).fetchall()
    ranked = []
    for row in rows:
        text = decrypt(row["text"], key).decode()
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        lexical = len(query_tokens & tokens) / max(len(query_tokens), 1)
        stored = json.loads(row["embedding"] or "[]")
        vector_score = cosine(query_vector, stored) if stored else 0.0
        score = (0.65 * lexical) + (0.35 * max(vector_score, 0.0))
        if lexical > 0 or vector_score > 0.15:
            ranked.append((score, row, text))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [(row, text) for _, row, text in ranked[:limit]]

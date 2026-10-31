import base64, hashlib, hmac, os

def new_case_key() -> bytes: return os.urandom(32)
def wrap_key(key: bytes) -> bytes:
    # Development envelope-key adapter. Replace with KMS/Vault in production.
    from .config import APP_SECRET
    mask = hashlib.sha256(APP_SECRET.encode()).digest()
    return bytes(a ^ b for a,b in zip(key, mask))
def unwrap_key(wrapped: bytes) -> bytes: return wrap_key(wrapped)
def encrypt(data: bytes, key: bytes) -> bytes:
    nonce = os.urandom(16); stream = hashlib.sha256(key + nonce).digest()
    body = bytes(v ^ stream[i % len(stream)] for i,v in enumerate(data))
    return nonce + body
def decrypt(data: bytes, key: bytes) -> bytes:
    nonce, body = data[:16], data[16:]; stream = hashlib.sha256(key + nonce).digest()
    return bytes(v ^ stream[i % len(stream)] for i,v in enumerate(body))

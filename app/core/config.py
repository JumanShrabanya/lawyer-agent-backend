import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "app.db"))
APP_SECRET = os.getenv("APP_SECRET", "development-only-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
ALLOW_OUTBOUND_INFERENCE = os.getenv("ALLOW_OUTBOUND_INFERENCE", "false").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b")

DATA_DIR.mkdir(parents=True, exist_ok=True)

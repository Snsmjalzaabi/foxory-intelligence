import os
from pathlib import Path

DATA = Path(os.getenv("FOXORY_DATA_DIR", "./data")).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA / 'foxory.db'}")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
SEARXNG_URL = os.getenv("SEARXNG_URL", "").rstrip("/")
# Set via environment; never stored in ordinary memory or the database.
TOKEN = os.getenv("FOXORY_TOKEN", "")
SECURE_COOKIES = os.getenv("FOXORY_SECURE_COOKIES", "0")
if SECURE_COOKIES not in {"0", "1"}:
    raise ValueError("FOXORY_SECURE_COOKIES must be 0 or 1")
SECURE_COOKIES = SECURE_COOKIES == "1"
MAX_UPLOAD = 10 * 1024 * 1024

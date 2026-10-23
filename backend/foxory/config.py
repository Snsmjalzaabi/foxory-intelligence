import os
from pathlib import Path

DATA = Path(os.getenv("FOXORY_DATA_DIR", "./data")).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA / 'foxory.db'}")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
SEARXNG_URL = os.getenv("SEARXNG_URL", "").rstrip("/")
# Set via environment; never stored in ordinary memory or the database.
TOKEN = os.getenv("FOXORY_TOKEN", "")
MAX_UPLOAD = 10 * 1024 * 1024

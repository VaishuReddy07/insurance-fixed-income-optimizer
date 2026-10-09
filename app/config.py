from datetime import datetime, timezone
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'portfolio.db'}")
API_KEY = os.getenv("API_KEY", "").strip()
if API_KEY and len(API_KEY) < 32:
    raise RuntimeError("API_KEY must contain at least 32 characters when authentication is enabled")
ECB_REFERENCE_ENABLED = os.getenv("ECB_REFERENCE_ENABLED", "true").lower() in {"1", "true", "yes"}
ECB_CACHE_SECONDS = int(os.getenv("ECB_CACHE_SECONDS", "900"))
ECB_TIMEOUT_SECONDS = float(os.getenv("ECB_TIMEOUT_SECONDS", "12"))
DASHBOARD_FILE = BASE_DIR / "app" / "static" / "index.html"

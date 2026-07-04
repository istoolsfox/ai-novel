"""Vercel Python Runtime entrypoint.

Vercel loads the top-level `app` variable as an ASGI application. The real
FastAPI app lives in backend.app.interfaces.main, so this file only prepares a
safe temporary data directory for preview deployments and re-exports the app.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.getenv("AI_NOVEL_DATA_DIR", "/tmp/ai-novel-data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("AI_NOVEL_DATA_DIR", str(DATA_DIR))
os.environ.setdefault("AI_NOVEL_DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
os.environ.setdefault("AI_NOVEL_MODEL_TIMEOUT_SECONDS", "90")
os.environ.setdefault("AI_NOVEL_GENERATION_TIMEOUT_SECONDS", "120")

from backend.app.interfaces.main import app  # noqa: E402,F401

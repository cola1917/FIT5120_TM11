"""Load the project root .env before reading os.environ, and normalise the HF Token env var name."""
from __future__ import annotations

import os
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent.parent


def ensure_dotenv_loaded() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    # Prefer .env (local secrets, do not commit). Fall back to .env.example for local dev if HF_TOKEN is missing.
    load_dotenv(_API_ROOT / ".env", override=True)
    token = (os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or "").strip()
    if not token:
        load_dotenv(_API_ROOT / ".env.example", override=False)
        token = (os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or "").strip()

    if token:
        os.environ["HF_TOKEN"] = token

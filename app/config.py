"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CREDENTIALS_PATH = Path(
    os.getenv("CREDENTIALS_PATH", PROJECT_ROOT / "credentials.json")
)
TOKEN_PATH = Path(os.getenv("TOKEN_PATH", PROJECT_ROOT / "token.json"))
MAX_EMAILS_PER_RUN = int(os.getenv("MAX_EMAILS_PER_RUN", "20"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Runtime mode: dry_run (default) | approval | automatic
# Lesson 4 only uses dry_run. Later lessons add the others.
ALLOWED_MODES = frozenset({"dry_run", "approval", "automatic"})
MODE = os.getenv("MODE", "dry_run").strip().lower()
if MODE not in ALLOWED_MODES:
    raise ValueError(f"Invalid MODE={MODE!r}. Allowed: {sorted(ALLOWED_MODES)}")

# Read-only scope only until Lesson 5+.
GMAIL_SCOPES = ("https://www.googleapis.com/auth/gmail.readonly",)

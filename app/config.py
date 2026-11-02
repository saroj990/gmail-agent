"""Application configuration loaded from environment variables.

Values come from a local `.env` file (never committed). Defaults keep the
agent in dry-run with a local Ollama model so Gmail is not modified by accident.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# OAuth client JSON from Google Cloud (Desktop app). Token is created on first login.
CREDENTIALS_PATH = Path(
    os.getenv("CREDENTIALS_PATH", PROJECT_ROOT / "credentials.json")
)
TOKEN_PATH = Path(os.getenv("TOKEN_PATH", PROJECT_ROOT / "token.json"))
# Max unprocessed inbox messages to classify per run (pages through Inbox if needed).
MAX_EMAILS_PER_RUN = int(os.getenv("MAX_EMAILS_PER_RUN", "20"))

# Gmail search query when fetching mail for a run (default: Inbox only).
GMAIL_INBOX_QUERY = os.getenv("GMAIL_INBOX_QUERY", "in:inbox").strip() or "in:inbox"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Classifier backend: ollama (local, default) | gemini (Google AI Studio)
ALLOWED_LLM_PROVIDERS = frozenset({"ollama", "gemini"})
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
if LLM_PROVIDER not in ALLOWED_LLM_PROVIDERS:
    raise ValueError(
        f"Invalid LLM_PROVIDER={LLM_PROVIDER!r}. Allowed: {sorted(ALLOWED_LLM_PROVIDERS)}"
    )

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_API_BASE_URL = os.getenv(
    "GEMINI_API_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta",
).rstrip("/")

# Runtime mode: dry_run (default) | approval | automatic
ALLOWED_MODES = frozenset({"dry_run", "approval", "automatic"})
MODE = os.getenv("MODE", "dry_run").strip().lower()
if MODE not in ALLOWED_MODES:
    raise ValueError(f"Invalid MODE={MODE!r}. Allowed: {sorted(ALLOWED_MODES)}")

GMAIL_LABEL = os.getenv("GMAIL_LABEL", "To Process")

# Minimum confidence required before labeling + archiving.
CONFIDENCE_THRESHOLD = float(
    os.getenv("CONFIDENCE_THRESHOLD", os.getenv("CLASSIFICATION_THRESHOLD", "0.95"))
)

# Lesson 10: local SQLite audit / dedupe store.
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", PROJECT_ROOT / "data" / "decisions.db")
)

# Web UI preferences (non-secret). Overrides the env defaults above for UI runs only.
SETTINGS_PATH = Path(
    os.getenv("SETTINGS_PATH", PROJECT_ROOT / "data" / "settings.json")
)

# Lesson 5+: modify scope is required to create/apply labels.
# This does NOT allow permanent delete.
GMAIL_SCOPES = ("https://www.googleapis.com/auth/gmail.modify",)

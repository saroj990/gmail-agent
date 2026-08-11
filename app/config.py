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
MAX_EMAILS_PER_RUN = int(os.getenv("MAX_EMAILS_PER_RUN", "10"))

# Read-only scope only for Lesson 1.
GMAIL_SCOPES = ("https://www.googleapis.com/auth/gmail.readonly",)

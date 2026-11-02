"""Web UI preferences stored as JSON (non-secret config only).

Defaults come from app.config (env / .env). The Gemini API key is never stored
here; it stays in the local .env file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import (
    CONFIDENCE_THRESHOLD,
    GEMINI_MODEL,
    GMAIL_LABEL,
    LLM_PROVIDER,
    MAX_EMAILS_PER_RUN,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    SETTINGS_PATH,
)

logger = logging.getLogger(__name__)


class Settings(BaseModel):
    """User-editable preferences applied to UI-triggered runs."""

    llm_provider: Literal["ollama", "gemini"]
    ollama_base_url: str = Field(min_length=1)
    ollama_model: str = Field(min_length=1)
    gemini_model: str = Field(min_length=1)
    gmail_label: str = Field(min_length=1, max_length=225)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    max_emails_per_run: int = Field(ge=1, le=100)

    @field_validator("ollama_model", "gemini_model", "gmail_label")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def _check_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://")
        return value

    def classifier_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for app.classifier.classify()."""
        if self.llm_provider == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
            }
        return {"provider": "gemini", "model": self.gemini_model}


def default_settings() -> Settings:
    """Settings derived from env / .env values."""
    return Settings(
        llm_provider=LLM_PROVIDER,  # type: ignore[arg-type]
        ollama_base_url=OLLAMA_BASE_URL,
        ollama_model=OLLAMA_MODEL,
        gemini_model=GEMINI_MODEL,
        gmail_label=GMAIL_LABEL,
        confidence_threshold=CONFIDENCE_THRESHOLD,
        max_emails_per_run=max(1, min(MAX_EMAILS_PER_RUN, 100)),
    )


class SettingsStore:
    """Load/save Settings as JSON, falling back to env defaults."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or SETTINGS_PATH)

    def load(self) -> Settings:
        defaults = default_settings()
        if not self.path.exists():
            return defaults
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                raise ValueError("settings file must contain a JSON object")
            return Settings.model_validate({**defaults.model_dump(), **saved})
        except (OSError, ValueError, ValidationError) as exc:
            logger.warning("Ignoring invalid settings file %s: %s", self.path, exc)
            return defaults

    def save(self, settings: Settings) -> Settings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        return settings

    def reset(self) -> Settings:
        """Drop saved preferences and return to env defaults."""
        self.path.unlink(missing_ok=True)
        return default_settings()

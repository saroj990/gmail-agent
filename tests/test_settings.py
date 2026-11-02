"""Tests for web UI preferences storage."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.settings import Settings, SettingsStore, default_settings


def test_load_returns_env_defaults_when_file_missing(tmp_path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    assert store.load() == default_settings()


def test_save_and_load_round_trip(tmp_path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    saved = default_settings().model_copy(
        update={"llm_provider": "gemini", "confidence_threshold": 0.8, "gmail_label": "Later"}
    )
    store.save(saved)
    assert store.load() == saved


def test_invalid_file_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert SettingsStore(path).load() == default_settings()


def test_partial_file_merges_with_defaults(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"max_emails_per_run": 5}', encoding="utf-8")
    loaded = SettingsStore(path).load()
    assert loaded.max_emails_per_run == 5
    assert loaded.gmail_label == default_settings().gmail_label


def test_reset_deletes_file(tmp_path) -> None:
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.save(default_settings())
    assert store.reset() == default_settings()
    assert not path.exists()


@pytest.mark.parametrize(
    "update",
    [
        {"confidence_threshold": 1.5},
        {"max_emails_per_run": 0},
        {"gmail_label": "   "},
        {"ollama_base_url": "localhost:11434"},
        {"llm_provider": "openai"},
    ],
)
def test_validation_rejects_bad_values(update) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({**default_settings().model_dump(), **update})


def test_classifier_kwargs_per_provider() -> None:
    base = default_settings()
    ollama = base.model_copy(update={"llm_provider": "ollama", "ollama_model": "qwen3:8b"})
    assert ollama.classifier_kwargs() == {
        "provider": "ollama",
        "base_url": ollama.ollama_base_url,
        "model": "qwen3:8b",
    }
    gemini = base.model_copy(update={"llm_provider": "gemini"})
    assert gemini.classifier_kwargs() == {"provider": "gemini", "model": gemini.gemini_model}

"""Unit tests for the Ollama classifier (mocked HTTP)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.classifier import (
    ClassifierError,
    build_user_prompt,
    classify,
    extract_json_object,
    parse_classification,
    unknown_result,
)
from app.models import Action, Category, ClassificationResult, EmailMessage, Importance


SAMPLE_EMAIL = EmailMessage(
    message_id="msg-1",
    thread_id="t1",
    sender="LinkedIn <notifications@linkedin.com>",
    recipient="me@gmail.com",
    subject="Someone viewed your profile",
    date="Tue, 11 Aug 2026 10:00:00 +0000",
    body="15 people viewed your profile this week.",
    snippet="15 people viewed your profile",
)


def test_parse_classification_valid() -> None:
    result = parse_classification(
        {
            "category": "TO_PROCESS",
            "importance": "LOW",
            "confidence": 0.97,
            "reason": "Promotional LinkedIn notification.",
            "action": "LABEL_AND_ARCHIVE",
        }
    )
    assert result.category == Category.TO_PROCESS
    assert result.action == Action.LABEL_AND_ARCHIVE
    assert result.confidence == 0.97


def test_parse_classification_aligns_mismatched_action() -> None:
    result = parse_classification(
        {
            "category": "IMPORTANT",
            "importance": "HIGH",
            "confidence": 0.9,
            "reason": "Interview invite",
            "action": "NO_ACTION",
        }
    )
    assert result.action == Action.LEAVE_IN_INBOX


def test_parse_classification_rejects_forbidden_action() -> None:
    with pytest.raises(ValueError, match="Forbidden action"):
        parse_classification(
            {
                "category": "TO_PROCESS",
                "importance": "LOW",
                "confidence": 0.9,
                "reason": "spam",
                "action": "DELETE",
            }
        )


def test_parse_classification_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        parse_classification(
            {
                "category": "SPAM",
                "importance": "LOW",
                "confidence": 0.5,
                "reason": "nope",
                "action": "NO_ACTION",
            }
        )


def test_classification_result_never_allows_delete_enum() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            category=Category.TO_PROCESS,
            importance=Importance.LOW,
            confidence=0.9,
            reason="x",
            action="DELETE",  # type: ignore[arg-type]
        )


def test_extract_json_object_from_fenced_text() -> None:
    text = 'Here you go:\n```json\n{"category": "UNKNOWN"}\n```'
    assert extract_json_object(text) == {"category": "UNKNOWN"}


def test_unknown_result_is_safe() -> None:
    result = unknown_result("bad json")
    assert result.category == Category.UNKNOWN
    assert result.action == Action.NO_ACTION
    assert result.confidence == 0.0


def test_build_user_prompt_includes_key_fields() -> None:
    prompt = build_user_prompt(SAMPLE_EMAIL)
    assert "LinkedIn" in prompt
    assert "Someone viewed your profile" in prompt
    assert "15 people viewed your profile" in prompt


def test_classify_happy_path() -> None:
    payload = {
        "message": {
            "content": json.dumps(
                {
                    "category": "TO_PROCESS",
                    "importance": "LOW",
                    "confidence": 0.99,
                    "reason": "Routine social notification",
                    "action": "LABEL_AND_ARCHIVE",
                }
            )
        }
    }

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("app.classifier.urllib.request.urlopen", return_value=mock_response):
        result = classify(SAMPLE_EMAIL, provider="ollama")

    assert result.category == Category.TO_PROCESS
    assert result.action == Action.LABEL_AND_ARCHIVE


def test_classify_invalid_model_output_falls_back_to_unknown() -> None:
    payload = {"message": {"content": "not-json-at-all"}}
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("app.classifier.urllib.request.urlopen", return_value=mock_response):
        result = classify(SAMPLE_EMAIL, provider="ollama")

    assert result.category == Category.UNKNOWN
    assert result.action == Action.NO_ACTION


def test_classify_forbidden_action_falls_back_to_unknown() -> None:
    payload = {
        "message": {
            "content": json.dumps(
                {
                    "category": "TO_PROCESS",
                    "importance": "LOW",
                    "confidence": 0.9,
                    "reason": "bad",
                    "action": "DELETE",
                }
            )
        }
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("app.classifier.urllib.request.urlopen", return_value=mock_response):
        result = classify(SAMPLE_EMAIL, provider="ollama")

    assert result.category == Category.UNKNOWN
    assert result.action == Action.NO_ACTION


def test_classify_raises_when_ollama_unreachable() -> None:
    import urllib.error

    with patch(
        "app.classifier.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        with pytest.raises(ClassifierError, match="Could not reach Ollama"):
            classify(SAMPLE_EMAIL, provider="ollama")


def test_classify_gemini_happy_path() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "category": "IMPORTANT",
                                    "importance": "HIGH",
                                    "confidence": 0.91,
                                    "reason": "Interview invitation",
                                    "action": "LEAVE_IN_INBOX",
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("app.classifier.urllib.request.urlopen", return_value=mock_response):
        result = classify(
            SAMPLE_EMAIL,
            provider="gemini",
            api_key="test-key",
            model="gemini-2.5-flash",
        )

    assert result.category == Category.IMPORTANT
    assert result.action == Action.LEAVE_IN_INBOX
    assert result.confidence == 0.91


def test_classify_gemini_requires_api_key() -> None:
    with pytest.raises(ClassifierError, match="GEMINI_API_KEY"):
        classify(SAMPLE_EMAIL, provider="gemini", api_key="")


def test_classify_gemini_empty_response_raises() -> None:
    payload = {"candidates": [{"content": {"parts": []}}]}
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("app.classifier.urllib.request.urlopen", return_value=mock_response):
        with pytest.raises(ClassifierError, match="empty message"):
            classify(SAMPLE_EMAIL, provider="gemini", api_key="test-key")

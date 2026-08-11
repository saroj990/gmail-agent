"""Tests for the CLI helpers."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from app.agent import AgentResult
from app.models import Action, Category, ClassificationResult, EmailMessage, Importance
from main import fetch_recent_emails, print_classification


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def test_print_classification_format(capsys) -> None:
    result = AgentResult(
        email=EmailMessage(
            message_id="1",
            thread_id="t1",
            sender="LinkedIn <notifications@linkedin.com>",
            subject="Someone viewed your profile",
        ),
        decision=ClassificationResult(
            category=Category.TO_PROCESS,
            importance=Importance.LOW,
            confidence=0.99,
            reason="Routine social notification",
            action=Action.LABEL_AND_ARCHIVE,
        ),
        action=Action.LABEL_AND_ARCHIVE,
        execution_note="skipped (dry_run): LABEL_AND_ARCHIVE",
    )

    print_classification(1, result)
    output = capsys.readouterr().out

    assert "[1]" in output
    assert "Message-ID: 1" in output
    assert "Category: TO_PROCESS" in output
    assert "Action: LABEL_AND_ARCHIVE" in output
    assert "Confidence: 0.99" in output
    assert "Execution: skipped (dry_run): LABEL_AND_ARCHIVE" in output


def test_fetch_recent_emails_parses_messages() -> None:
    raw = {
        "id": "msg-1",
        "threadId": "t1",
        "snippet": "Hello",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "a@example.com"},
                {"name": "To", "value": "me@gmail.com"},
                {"name": "Subject", "value": "Hi"},
                {"name": "Date", "value": "today"},
            ],
            "body": {"data": _b64url("Hello body")},
        },
    }

    with patch("main.GmailAgent") as mock_agent_cls:
        instance = MagicMock()
        instance.fetch_raw_messages.return_value = [raw]
        mock_agent_cls.return_value = instance
        emails = fetch_recent_emails(max_results=5)

    assert len(emails) == 1
    assert emails[0].sender == "a@example.com"
    assert emails[0].body == "Hello body"

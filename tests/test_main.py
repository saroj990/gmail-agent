"""Tests for the CLI output helpers."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from app.models import EmailMessage
from main import fetch_recent_emails, print_emails


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def test_print_emails_format(capsys) -> None:
    print_emails(
        [
            EmailMessage(
                message_id="1",
                thread_id="t1",
                sender="LinkedIn <notifications@linkedin.com>",
                recipient="me@gmail.com",
                subject="Someone viewed your profile",
                date="Mon, 10 Aug 2026 10:00:00 +0000",
                body="Profile view details",
                snippet="Someone viewed your profile",
            )
        ]
    )

    output = capsys.readouterr().out
    assert "Found 1 emails" in output
    assert "From: LinkedIn <notifications@linkedin.com>" in output
    assert "Subject: Someone viewed your profile" in output
    assert "Body: Profile view details" in output


def test_fetch_recent_emails_parses_messages() -> None:
    service = MagicMock()
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

    with (
        patch("main.get_service", return_value=service) as mock_get_service,
        patch(
            "main.list_messages",
            return_value=[{"id": "msg-1", "threadId": "t1"}],
        ) as mock_list,
        patch("main.get_message", return_value=raw) as mock_get,
    ):
        emails = fetch_recent_emails(max_results=5)

    mock_get_service.assert_called_once()
    mock_list.assert_called_once_with(service, max_results=5)
    mock_get.assert_called_once_with(service, "msg-1")
    assert len(emails) == 1
    assert emails[0].sender == "a@example.com"
    assert emails[0].body == "Hello body"

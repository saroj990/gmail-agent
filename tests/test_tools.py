"""Tests for allowlisted Gmail tools (Lesson 8)."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.tools import ALLOWED_TOOLS, FORBIDDEN_TOOLS, GmailTools, ToolError


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def test_allowed_tools_match_lesson() -> None:
    assert ALLOWED_TOOLS == {
        "get_recent_emails",
        "read_email",
        "apply_label",
        "archive_email",
    }


def test_invoke_rejects_unknown_tool() -> None:
    tools = GmailTools(service=MagicMock())
    with pytest.raises(ToolError, match="Unknown tool"):
        tools.invoke(" invent_something ")


def test_invoke_rejects_forbidden_tools() -> None:
    tools = GmailTools(service=MagicMock())
    for name in ("delete", "send", "reply", "move_to_spam", "trash"):
        with pytest.raises(ToolError, match="Forbidden tool"):
            tools.invoke(name)


def test_forbidden_and_allowed_do_not_overlap() -> None:
    assert ALLOWED_TOOLS.isdisjoint(FORBIDDEN_TOOLS)


def test_get_recent_emails_and_read_email() -> None:
    service = MagicMock()
    tools = GmailTools(service=service)
    raw = {
        "id": "msg-1",
        "threadId": "t1",
        "snippet": "Hi",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "a@example.com"},
                {"name": "Subject", "value": "Hello"},
            ],
            "body": {"data": _b64url("Hello body")},
        },
    }

    with (
        patch("app.tools.list_messages", return_value=[{"id": "msg-1", "threadId": "t1"}]),
        patch("app.tools.get_message", return_value=raw),
    ):
        stubs = tools.invoke("get_recent_emails", max_results=1)
        email = tools.invoke("read_email", message_id="msg-1")

    assert stubs[0]["id"] == "msg-1"
    assert email.subject == "Hello"
    assert email.body == "Hello body"


def test_apply_label_and_archive_email_tools() -> None:
    service = MagicMock()
    tools = GmailTools(service=service)

    with (
        patch("app.tools.apply_to_process_label", return_value="To Process") as mock_label,
        patch("app.tools.archive_message") as mock_archive,
    ):
        label = tools.invoke("apply_label", message_id="msg-1")
        archived = tools.invoke("archive_email", message_id="msg-1")

    assert label == "To Process"
    assert archived == "msg-1"
    mock_label.assert_called_once()
    mock_archive.assert_called_once_with(service, "msg-1")

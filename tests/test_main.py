"""Tests for the Lesson 1 CLI output helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from main import fetch_recent_summaries, print_summaries


def test_print_summaries_format(capsys) -> None:
    print_summaries(
        [
            {
                "from": "LinkedIn <notifications@linkedin.com>",
                "subject": "Someone viewed your profile",
                "date": "Mon, 10 Aug 2026 10:00:00 +0000",
                "snippet": "Someone viewed your profile",
            }
        ]
    )

    output = capsys.readouterr().out
    assert "Found 1 emails" in output
    assert "From: LinkedIn <notifications@linkedin.com>" in output
    assert "Subject: Someone viewed your profile" in output
    assert "Date: Mon, 10 Aug 2026 10:00:00 +0000" in output
    assert "Snippet: Someone viewed your profile" in output


def test_fetch_recent_summaries_uses_gmail_client() -> None:
    service = MagicMock()

    with (
        patch("main.get_service", return_value=service) as mock_get_service,
        patch(
            "main.list_messages",
            return_value=[{"id": "msg-1", "threadId": "t1"}],
        ) as mock_list,
        patch(
            "main.get_message",
            return_value={
                "id": "msg-1",
                "snippet": "Hello",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "a@example.com"},
                        {"name": "Subject", "value": "Hi"},
                        {"name": "Date", "value": "today"},
                    ]
                },
            },
        ) as mock_get,
    ):
        summaries = fetch_recent_summaries(max_results=5)

    mock_get_service.assert_called_once()
    mock_list.assert_called_once_with(service, max_results=5)
    mock_get.assert_called_once_with(service, "msg-1")
    assert summaries == [
        {
            "from": "a@example.com",
            "subject": "Hi",
            "date": "today",
            "snippet": "Hello",
        }
    ]

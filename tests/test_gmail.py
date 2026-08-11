"""Unit tests for the Lesson 1 Gmail client helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.gmail import (
    GmailAuthError,
    get_header,
    get_message,
    get_service,
    list_messages,
    summarize_message,
)


SAMPLE_MESSAGE = {
    "id": "msg-1",
    "snippet": "Someone viewed your profile",
    "payload": {
        "headers": [
            {"name": "From", "value": "LinkedIn <notifications@linkedin.com>"},
            {"name": "Subject", "value": "Someone viewed your profile"},
            {"name": "Date", "value": "Mon, 10 Aug 2026 10:00:00 +0000"},
        ]
    },
}


def test_get_header_is_case_insensitive() -> None:
    assert get_header(SAMPLE_MESSAGE, "from") == "LinkedIn <notifications@linkedin.com>"
    assert get_header(SAMPLE_MESSAGE, "SUBJECT") == "Someone viewed your profile"


def test_get_header_missing_returns_empty_string() -> None:
    assert get_header(SAMPLE_MESSAGE, "X-Missing") == ""


def test_summarize_message() -> None:
    summary = summarize_message(SAMPLE_MESSAGE)
    assert summary == {
        "from": "LinkedIn <notifications@linkedin.com>",
        "subject": "Someone viewed your profile",
        "date": "Mon, 10 Aug 2026 10:00:00 +0000",
        "snippet": "Someone viewed your profile",
    }


def test_list_messages_returns_message_stubs() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "1", "threadId": "t1"}, {"id": "2", "threadId": "t2"}]
    }

    result = list_messages(service, max_results=2)

    assert len(result) == 2
    assert result[0]["id"] == "1"
    service.users.return_value.messages.return_value.list.assert_called_once_with(
        userId="me",
        maxResults=2,
    )


def test_list_messages_empty_mailbox() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {}

    assert list_messages(service) == []


def test_get_message_fetches_by_id() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
        SAMPLE_MESSAGE
    )

    result = get_message(service, "msg-1")

    assert result["id"] == "msg-1"
    service.users.return_value.messages.return_value.get.assert_called_once_with(
        userId="me",
        id="msg-1",
        format="full",
    )


def test_get_service_raises_when_credentials_missing(tmp_path) -> None:
    missing = tmp_path / "missing-credentials.json"
    token = tmp_path / "token.json"

    with pytest.raises(GmailAuthError, match="Missing OAuth client file"):
        get_service(credentials_path=missing, token_path=token)


def test_get_service_builds_client_with_valid_token(tmp_path) -> None:
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}", encoding="utf-8")
    token_file = tmp_path / "token.json"

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.scopes = ["https://www.googleapis.com/auth/gmail.modify"]

    with (
        patch("app.gmail.Credentials.from_authorized_user_file", return_value=fake_creds),
        patch("app.gmail.build") as mock_build,
    ):
        token_file.write_text("{}", encoding="utf-8")
        service = get_service(credentials_path=credentials_file, token_path=token_file)

    mock_build.assert_called_once_with(
        "gmail", "v1", credentials=fake_creds, cache_discovery=False
    )
    assert service is mock_build.return_value

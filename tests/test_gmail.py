"""Unit tests for the Lesson 1 Gmail client helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError, TransportError

from app.gmail import (
    GmailAuthError,
    GmailNotSignedInError,
    collect_unprocessed_stubs,
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


def test_collect_unprocessed_stubs_skips_and_pages() -> None:
    service = MagicMock()
    list_api = service.users.return_value.messages.return_value.list
    list_api.return_value.execute.side_effect = [
        {
            "messages": [{"id": "seen", "threadId": "t0"}, {"id": "new-1", "threadId": "t1"}],
            "nextPageToken": "page-2",
        },
        {"messages": [{"id": "new-2", "threadId": "t2"}]},
    ]
    skip = {"seen"}

    stubs, skipped = collect_unprocessed_stubs(
        service,
        limit=2,
        should_skip=lambda mid: mid in skip,
        query="in:inbox",
        page_size=2,
    )

    assert skipped == 1
    assert [s["id"] for s in stubs] == ["new-1", "new-2"]
    assert list_api.call_count == 2


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


def test_get_service_non_interactive_without_token_raises(tmp_path) -> None:
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}", encoding="utf-8")

    with (
        patch("app.gmail.InstalledAppFlow") as mock_flow,
        pytest.raises(GmailNotSignedInError),
    ):
        get_service(
            credentials_path=credentials_file,
            token_path=tmp_path / "token.json",
            interactive=False,
        )
    mock_flow.from_client_secrets_file.assert_not_called()


def test_get_service_unreadable_token_raises_auth_error(tmp_path) -> None:
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}", encoding="utf-8")
    token_file = tmp_path / "token.json"
    token_file.write_text("{}", encoding="utf-8")

    with pytest.raises(GmailAuthError, match="unreadable"):
        get_service(credentials_path=credentials_file, token_path=token_file)


def _expired_creds(refresh_side_effect: Exception) -> MagicMock:
    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "refresh-token"
    creds.scopes = ["https://www.googleapis.com/auth/gmail.modify"]
    creds.refresh.side_effect = refresh_side_effect
    return creds


def test_get_service_raises_auth_error_when_refresh_token_rejected(tmp_path) -> None:
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}", encoding="utf-8")
    token_file = tmp_path / "token.json"
    token_file.write_text("{}", encoding="utf-8")
    creds = _expired_creds(
        RefreshError("invalid_grant: Bad Request", {"error": "invalid_grant"})
    )

    with (
        patch("app.gmail.Credentials.from_authorized_user_file", return_value=creds),
        patch("app.gmail.build") as mock_build,
        pytest.raises(GmailAuthError, match="no longer valid") as excinfo,
    ):
        get_service(credentials_path=credentials_file, token_path=token_file)

    assert str(token_file) in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RefreshError)
    mock_build.assert_not_called()
    assert token_file.read_text(encoding="utf-8") == "{}"


def test_get_service_raises_auth_error_when_google_unreachable(tmp_path) -> None:
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}", encoding="utf-8")
    token_file = tmp_path / "token.json"
    token_file.write_text("{}", encoding="utf-8")
    creds = _expired_creds(TransportError("connection refused"))

    with (
        patch("app.gmail.Credentials.from_authorized_user_file", return_value=creds),
        pytest.raises(GmailAuthError, match="Could not reach Google"),
    ):
        get_service(credentials_path=credentials_file, token_path=token_file)

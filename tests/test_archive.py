"""Unit tests for archive_message."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.gmail import archive_message


def test_archive_message_removes_inbox_label() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.modify.return_value.execute.return_value = {
        "id": "msg-1",
        "labelIds": ["Label_9"],
    }

    result = archive_message(service, "msg-1")

    assert result["id"] == "msg-1"
    service.users.return_value.messages.return_value.modify.assert_called_once_with(
        userId="me",
        id="msg-1",
        body={"removeLabelIds": ["INBOX"]},
    )

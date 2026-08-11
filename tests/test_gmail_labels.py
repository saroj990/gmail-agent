"""Unit tests for Gmail label helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.gmail import apply_label, create_label, ensure_label, get_label_id


def test_get_label_id_finds_exact_name() -> None:
    service = MagicMock()
    service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
        "labels": [
            {"id": "Label_1", "name": "Inbox"},
            {"id": "Label_9", "name": "To Process"},
        ]
    }

    assert get_label_id(service, "To Process") == "Label_9"
    assert get_label_id(service, "Missing") is None


def test_create_label_returns_id() -> None:
    service = MagicMock()
    service.users.return_value.labels.return_value.create.return_value.execute.return_value = {
        "id": "Label_42",
        "name": "To Process",
    }

    label_id = create_label(service, "To Process")

    assert label_id == "Label_42"
    service.users.return_value.labels.return_value.create.assert_called_once()


def test_ensure_label_returns_existing() -> None:
    service = MagicMock()
    service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
        "labels": [{"id": "Label_9", "name": "To Process"}]
    }

    assert ensure_label(service, "To Process") == "Label_9"
    service.users.return_value.labels.return_value.create.assert_not_called()


def test_ensure_label_creates_when_missing() -> None:
    service = MagicMock()
    service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
        "labels": []
    }
    service.users.return_value.labels.return_value.create.return_value.execute.return_value = {
        "id": "Label_7",
        "name": "To Process",
    }

    assert ensure_label(service, "To Process") == "Label_7"


def test_apply_label_modifies_message_without_removing_inbox() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.modify.return_value.execute.return_value = {
        "id": "msg-1",
        "labelIds": ["INBOX", "Label_9"],
    }

    result = apply_label(service, "msg-1", "Label_9")

    assert result["id"] == "msg-1"
    service.users.return_value.messages.return_value.modify.assert_called_once_with(
        userId="me",
        id="msg-1",
        body={"addLabelIds": ["Label_9"]},
    )

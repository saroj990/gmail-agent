"""Tests for action gating, labels, and archive."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.actions import (
    apply_to_process_label,
    execute_decision,
    gmail_writes_allowed,
    label_and_archive,
    meets_archive_guards,
    meets_content_guards,
    proposed_action,
)
from app.models import Action, Category, ClassificationResult, Importance


def _decision(
    *,
    action: Action = Action.LABEL_AND_ARCHIVE,
    category: Category = Category.TO_PROCESS,
    confidence: float = 0.99,
) -> ClassificationResult:
    return ClassificationResult(
        category=category,
        importance=Importance.LOW,
        confidence=confidence,
        reason="promo",
        action=action,
    )


def test_gmail_writes_not_allowed_in_dry_run() -> None:
    assert gmail_writes_allowed("dry_run") is False


def test_gmail_writes_allowed_in_later_modes() -> None:
    assert gmail_writes_allowed("approval") is True
    assert gmail_writes_allowed("automatic") is True


def test_meets_content_guards_ignores_mode() -> None:
    ok, _ = meets_content_guards(_decision(confidence=0.99), threshold=0.95)
    assert ok is True
    ok, reason = meets_content_guards(_decision(confidence=0.5), threshold=0.95)
    assert ok is False
    assert "confidence" in reason


def test_meets_archive_guards_requires_to_process_and_confidence() -> None:
    ok, _ = meets_archive_guards(_decision(), mode="automatic", threshold=0.95)
    assert ok is True

    ok, reason = meets_archive_guards(
        _decision(confidence=0.5), mode="automatic", threshold=0.95
    )
    assert ok is False
    assert "confidence" in reason

    ok, reason = meets_archive_guards(
        _decision(category=Category.IMPORTANT, action=Action.LEAVE_IN_INBOX),
        mode="automatic",
        threshold=0.95,
    )
    assert ok is False
    assert "IMPORTANT" in reason


def test_execute_decision_skips_in_dry_run() -> None:
    note = execute_decision(_decision(), mode="dry_run")
    assert note.startswith("skipped (dry_run)")
    assert "LABEL_AND_ARCHIVE" in note


def test_execute_decision_skips_low_confidence() -> None:
    note = execute_decision(
        _decision(confidence=0.5),
        mode="automatic",
        service=MagicMock(),
        message_id="msg-1",
    )
    assert note.startswith("skipped (confidence")
    assert "LABEL_AND_ARCHIVE" in note


def test_execute_decision_labels_and_archives_when_allowed() -> None:
    service = MagicMock()
    with patch("app.actions.label_and_archive", return_value="To Process") as mock_fn:
        note = execute_decision(
            _decision(),
            mode="automatic",
            service=service,
            message_id="msg-1",
        )

    mock_fn.assert_called_once_with(service, "msg-1")
    assert note == "labeled 'To Process' and archived"


def test_execute_decision_no_write_for_important() -> None:
    note = execute_decision(
        _decision(action=Action.LEAVE_IN_INBOX, category=Category.IMPORTANT),
        mode="automatic",
        service=MagicMock(),
        message_id="msg-1",
    )
    assert note == "no write: LEAVE_IN_INBOX"


def test_execute_decision_requires_ids_for_label_action() -> None:
    with pytest.raises(ValueError, match="service and message_id"):
        execute_decision(_decision(), mode="automatic")


def test_apply_to_process_label_ensures_and_applies() -> None:
    service = MagicMock()
    with (
        patch("app.actions.ensure_label", return_value="Label_9") as mock_ensure,
        patch("app.actions.apply_label") as mock_apply,
    ):
        name = apply_to_process_label(service, "msg-1", label_name="To Process")

    assert name == "To Process"
    mock_ensure.assert_called_once_with(service, "To Process")
    mock_apply.assert_called_once_with(service, "msg-1", "Label_9")


def test_label_and_archive_calls_both_operations() -> None:
    service = MagicMock()
    with (
        patch("app.actions.apply_to_process_label", return_value="To Process") as mock_label,
        patch("app.actions.archive_message") as mock_archive,
    ):
        name = label_and_archive(service, "msg-1")

    assert name == "To Process"
    mock_label.assert_called_once_with(service, "msg-1", label_name=None)
    mock_archive.assert_called_once_with(service, "msg-1")


def test_proposed_action_returns_decision_action() -> None:
    assert proposed_action(_decision()) == Action.LABEL_AND_ARCHIVE

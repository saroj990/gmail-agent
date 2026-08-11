"""Tests for dry-run action gating and Lesson 5 label execution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.actions import (
    apply_to_process_label,
    execute_decision,
    gmail_writes_allowed,
    proposed_action,
)
from app.models import Action, Category, ClassificationResult, Importance


def _decision(
    action: Action = Action.LABEL_AND_ARCHIVE,
    category: Category = Category.TO_PROCESS,
) -> ClassificationResult:
    return ClassificationResult(
        category=category,
        importance=Importance.LOW,
        confidence=0.99,
        reason="promo",
        action=action,
    )


def test_gmail_writes_not_allowed_in_dry_run() -> None:
    assert gmail_writes_allowed("dry_run") is False


def test_gmail_writes_allowed_in_later_modes() -> None:
    assert gmail_writes_allowed("approval") is True
    assert gmail_writes_allowed("automatic") is True


def test_execute_decision_skips_in_dry_run() -> None:
    note = execute_decision(_decision(), mode="dry_run")
    assert note.startswith("skipped (dry_run)")
    assert "LABEL_AND_ARCHIVE" in note


def test_execute_decision_applies_label_only_when_allowed() -> None:
    service = MagicMock()
    with patch("app.actions.apply_to_process_label", return_value="To Process") as mock_apply:
        note = execute_decision(
            _decision(),
            mode="automatic",
            service=service,
            message_id="msg-1",
        )

    mock_apply.assert_called_once_with(service, "msg-1")
    assert "applied label: To Process" in note
    assert "archive deferred" in note


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


def test_proposed_action_returns_decision_action() -> None:
    assert proposed_action(_decision()) == Action.LABEL_AND_ARCHIVE

"""Tests for dry-run action gating."""

from __future__ import annotations

import pytest

from app.actions import execute_decision, gmail_writes_allowed, proposed_action
from app.models import Action, Category, ClassificationResult, Importance


def _decision() -> ClassificationResult:
    return ClassificationResult(
        category=Category.TO_PROCESS,
        importance=Importance.LOW,
        confidence=0.99,
        reason="promo",
        action=Action.LABEL_AND_ARCHIVE,
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


def test_execute_decision_not_implemented_outside_dry_run() -> None:
    with pytest.raises(NotImplementedError):
        execute_decision(_decision(), mode="automatic")


def test_proposed_action_returns_decision_action() -> None:
    assert proposed_action(_decision()) == Action.LABEL_AND_ARCHIVE

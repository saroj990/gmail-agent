"""Tests for SQLite decision memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import DecisionStore
from app.models import Action, Category, ClassificationResult, EmailMessage, Importance


def _email(message_id: str = "msg-1") -> EmailMessage:
    return EmailMessage(
        message_id=message_id,
        thread_id="t1",
        sender="a@example.com",
        subject="Hello",
    )


def _decision() -> ClassificationResult:
    return ClassificationResult(
        category=Category.TO_PROCESS,
        importance=Importance.LOW,
        confidence=0.99,
        reason="promo",
        action=Action.LABEL_AND_ARCHIVE,
    )


def test_has_message_and_unique_constraint(tmp_path: Path) -> None:
    store = DecisionStore(db_path=tmp_path / "decisions.db")
    assert store.has_message("msg-1") is False

    store.save_decision(_email(), _decision(), execution_note="dry-run")
    assert store.has_message("msg-1") is True
    assert store.count() == 1

    # Upsert same message_id should not create a second row.
    store.save_decision(
        _email(),
        _decision(),
        execution_note="labeled and archived",
    )
    assert store.count() == 1
    row = store.get_decision("msg-1")
    assert row is not None
    assert row["execution_note"] == "labeled and archived"
    assert row["category"] == "TO_PROCESS"


def test_different_message_ids_are_separate(tmp_path: Path) -> None:
    store = DecisionStore(db_path=tmp_path / "decisions.db")
    store.save_decision(_email("msg-1"), _decision())
    store.save_decision(_email("msg-2"), _decision())
    assert store.count() == 2

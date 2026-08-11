"""Tests for interactive review helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.models import Action, Category, ClassificationResult, EmailMessage, Importance
from app.review import (
    ReviewItem,
    archive_candidates,
    print_summary,
    run_review,
    summarize,
)


def _item(
    *,
    category: Category,
    confidence: float,
    message_id: str = "msg-1",
) -> ReviewItem:
    action = {
        Category.IMPORTANT: Action.LEAVE_IN_INBOX,
        Category.TO_PROCESS: Action.LABEL_AND_ARCHIVE,
        Category.UNKNOWN: Action.NO_ACTION,
    }[category]
    return ReviewItem(
        email=EmailMessage(
            message_id=message_id,
            thread_id="t1",
            sender="a@example.com",
            subject="Hello",
        ),
        decision=ClassificationResult(
            category=category,
            importance=Importance.LOW,
            confidence=confidence,
            reason="test",
            action=action,
        ),
    )


def test_summarize_counts_and_candidates() -> None:
    items = [
        _item(category=Category.IMPORTANT, confidence=0.9, message_id="1"),
        _item(category=Category.TO_PROCESS, confidence=0.99, message_id="2"),
        _item(category=Category.TO_PROCESS, confidence=0.5, message_id="3"),
        _item(category=Category.UNKNOWN, confidence=0.2, message_id="4"),
    ]
    summary = summarize(items, threshold=0.8)
    assert summary["total"] == 4
    assert summary["IMPORTANT"] == 1
    assert summary["TO_PROCESS"] == 2
    assert summary["UNKNOWN"] == 1
    assert summary["archive_candidates"] == 1


def test_archive_candidates_filters_by_threshold() -> None:
    items = [
        _item(category=Category.TO_PROCESS, confidence=0.99, message_id="hi"),
        _item(category=Category.TO_PROCESS, confidence=0.4, message_id="lo"),
        _item(category=Category.IMPORTANT, confidence=0.99, message_id="imp"),
    ]
    candidates = archive_candidates(items, threshold=0.8)
    assert len(candidates) == 1
    assert candidates[0].email.message_id == "hi"


def test_print_summary_output(capsys) -> None:
    print_summary(
        {
            "total": 3,
            "IMPORTANT": 1,
            "TO_PROCESS": 1,
            "UNKNOWN": 1,
            "archive_candidates": 1,
        },
        threshold=0.8,
    )
    out = capsys.readouterr().out
    assert "SUMMARY" in out
    assert "Archive candidates:    1" in out


def test_run_review_archives_on_approval() -> None:
    service = MagicMock()
    item = _item(category=Category.TO_PROCESS, confidence=0.99, message_id="msg-9")
    answers = iter(["a"])

    with (
        patch("app.review.classify_batch", return_value=[item]),
        patch("app.review.label_and_archive") as mock_archive,
        patch("app.review.trash_message") as mock_trash,
    ):
        run_review(service, threshold=0.8, input_fn=lambda _prompt: next(answers))

    mock_archive.assert_called_once_with(service, "msg-9")
    mock_trash.assert_not_called()


def test_run_review_trash_requires_confirm() -> None:
    service = MagicMock()
    item = _item(category=Category.TO_PROCESS, confidence=0.99, message_id="msg-9")
    answers = iter(["t", "trash"])

    with (
        patch("app.review.classify_batch", return_value=[item]),
        patch("app.review.label_and_archive") as mock_archive,
        patch("app.review.trash_message") as mock_trash,
    ):
        run_review(service, threshold=0.8, input_fn=lambda _prompt: next(answers))

    mock_trash.assert_called_once_with(service, "msg-9")
    mock_archive.assert_not_called()

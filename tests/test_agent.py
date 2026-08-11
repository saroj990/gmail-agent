"""Tests for the Lesson 7 agent orchestration layer."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.agent import ALLOWED_ACTIONS, AgentError, GmailAgent, decide, validate_decision
from app.models import Action, Category, ClassificationResult, Importance


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _decision(
    *,
    category: Category = Category.TO_PROCESS,
    action: Action = Action.LABEL_AND_ARCHIVE,
    confidence: float = 0.99,
) -> ClassificationResult:
    return ClassificationResult(
        category=category,
        importance=Importance.LOW,
        confidence=confidence,
        reason="test",
        action=action,
    )


def test_allowed_actions_are_explicit() -> None:
    assert Action.LEAVE_IN_INBOX in ALLOWED_ACTIONS
    assert Action.LABEL_AND_ARCHIVE in ALLOWED_ACTIONS
    assert Action.NO_ACTION in ALLOWED_ACTIONS
    assert len(ALLOWED_ACTIONS) == 3


def test_validate_and_decide_important_leaves_inbox() -> None:
    decision = _decision(category=Category.IMPORTANT, action=Action.LEAVE_IN_INBOX)
    assert decide(decision) == Action.LEAVE_IN_INBOX


def test_validate_and_decide_unknown_is_no_action() -> None:
    decision = _decision(category=Category.UNKNOWN, action=Action.NO_ACTION)
    assert decide(decision) == Action.NO_ACTION


def test_validate_rejects_non_allowlisted_action() -> None:
    decision = _decision()
    decision.action = "DELETE"  # type: ignore[assignment]
    with pytest.raises(AgentError, match="not allowlisted"):
        validate_decision(decision)


def test_process_email_pipeline_dry_run() -> None:
    service = MagicMock()
    raw = {
        "id": "msg-1",
        "threadId": "t1",
        "snippet": "promo",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "news@example.com"},
                {"name": "Subject", "value": "Sale"},
            ],
            "body": {"data": _b64url("Big sale today")},
        },
    }
    decision = _decision()

    agent = GmailAgent(service=service, mode="dry_run")
    with (
        patch("app.agent.classify", return_value=decision),
        patch("app.agent.execute_decision", return_value="skipped (dry_run): LABEL_AND_ARCHIVE") as mock_exec,
    ):
        result = agent.process_email(raw)

    assert result.email.message_id == "msg-1"
    assert result.action == Action.LABEL_AND_ARCHIVE
    assert "skipped (dry_run)" in result.execution_note
    mock_exec.assert_called_once()


def test_run_fetches_and_processes() -> None:
    service = MagicMock()
    agent = GmailAgent(service=service, mode="dry_run", max_emails=1)
    raw = {
        "id": "msg-1",
        "threadId": "t1",
        "snippet": "x",
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": "Subject", "value": "Hi"}],
            "body": {"data": _b64url("hi")},
        },
    }

    with (
        patch.object(agent, "fetch_raw_messages", return_value=[raw]),
        patch.object(agent, "process_email") as mock_process,
    ):
        mock_process.return_value = MagicMock()
        results = agent.run()

    assert len(results) == 1
    mock_process.assert_called_once_with(raw)

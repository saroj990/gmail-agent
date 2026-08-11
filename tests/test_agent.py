"""Tests for the agent orchestration layer (Lessons 7–9)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.agent import (
    ALLOWED_ACTIONS,
    AgentError,
    GmailAgent,
    ask_approval,
    decide,
    format_proposal,
    validate_decision,
)
from app.database import DecisionStore
from app.models import Action, Category, ClassificationResult, EmailMessage, Importance
from app.tools import ToolError


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
    email = EmailMessage(
        message_id="msg-1",
        thread_id="t1",
        sender="news@example.com",
        subject="Sale",
        body="Big sale today",
    )
    decision = _decision()
    agent = GmailAgent(service=MagicMock(), mode="dry_run")

    with patch("app.agent.classify", return_value=decision):
        result = agent.process_email(email)

    assert result.email.message_id == "msg-1"
    assert result.action == Action.LABEL_AND_ARCHIVE
    assert "skipped (dry_run)" in result.execution_note


def test_execute_uses_tools_for_label_and_archive_automatic() -> None:
    email = EmailMessage(message_id="msg-1", thread_id="t1", subject="Sale")
    decision = _decision()
    tools = MagicMock()
    tools.invoke.side_effect = ["To Process", "msg-1"]
    agent = GmailAgent(service=MagicMock(), mode="automatic", tools=tools)

    note = agent.execute(email, decision, Action.LABEL_AND_ARCHIVE)

    assert note == "labeled 'To Process' and archived"
    assert tools.invoke.call_args_list[0].args[0] == "apply_label"
    assert tools.invoke.call_args_list[1].args[0] == "archive_email"


def test_approval_mode_executes_only_when_user_says_yes() -> None:
    email = EmailMessage(
        message_id="msg-1",
        thread_id="t1",
        sender="LinkedIn <x@linkedin.com>",
        subject="Someone viewed your profile",
    )
    decision = _decision()
    tools = MagicMock()
    tools.invoke.side_effect = ["To Process", "msg-1"]
    agent = GmailAgent(
        service=MagicMock(),
        mode="approval",
        tools=tools,
        input_fn=lambda _prompt: "y",
    )

    note = agent.execute(email, decision, Action.LABEL_AND_ARCHIVE)
    assert note == "labeled 'To Process' and archived"
    assert tools.invoke.call_count == 2


def test_approval_mode_declined_leaves_gmail_unchanged() -> None:
    email = EmailMessage(
        message_id="msg-1",
        thread_id="t1",
        sender="LinkedIn <x@linkedin.com>",
        subject="Someone viewed your profile",
    )
    decision = _decision()
    tools = MagicMock()
    agent = GmailAgent(
        service=MagicMock(),
        mode="approval",
        tools=tools,
        input_fn=lambda _prompt: "n",
    )

    note = agent.execute(email, decision, Action.LABEL_AND_ARCHIVE)
    assert note == "declined by user: LABEL_AND_ARCHIVE"
    tools.invoke.assert_not_called()


def test_ask_approval_defaults_to_no() -> None:
    email = EmailMessage(message_id="1", thread_id="t", sender="a", subject="b")
    decision = _decision()
    assert ask_approval(email, decision, Action.LABEL_AND_ARCHIVE, input_fn=lambda _: "") is False
    assert ask_approval(email, decision, Action.LABEL_AND_ARCHIVE, input_fn=lambda _: "y") is True


def test_format_proposal_matches_lesson_shape() -> None:
    email = EmailMessage(
        message_id="1",
        thread_id="t",
        sender="LinkedIn",
        subject="15 people viewed your profile",
    )
    text = format_proposal(email, _decision(), Action.LABEL_AND_ARCHIVE)
    assert "Email:" in text
    assert "AI Decision:" in text
    assert "TO_PROCESS" in text
    assert "Proposed action:" in text
    assert "archive" in text.lower()


def test_execute_cannot_call_forbidden_tool_names() -> None:
    tools = MagicMock()
    tools.invoke.side_effect = ToolError("Forbidden tool: delete")
    with pytest.raises(ToolError, match="Forbidden"):
        tools.invoke("delete")


def test_run_skips_cached_message_ids(tmp_path) -> None:
    email_new = EmailMessage(message_id="msg-new", thread_id="t1", subject="New")
    store = DecisionStore(db_path=tmp_path / "decisions.db")
    store.save_decision(
        EmailMessage(message_id="msg-old", thread_id="t0", subject="Old"),
        _decision(),
        execution_note="already done",
    )

    tools = MagicMock()
    tools.invoke.side_effect = [
        [{"id": "msg-old", "threadId": "t0"}, {"id": "msg-new", "threadId": "t1"}],
        email_new,
    ]
    agent = GmailAgent(
        service=MagicMock(),
        mode="dry_run",
        tools=tools,
        store=store,
    )

    with patch.object(agent, "process_email") as mock_process:
        mock_process.return_value = MagicMock()
        results = agent.run()

    assert agent.skipped_cached == 1
    assert len(results) == 1
    mock_process.assert_called_once_with(email_new)


def test_process_email_persists_decision(tmp_path) -> None:
    email = EmailMessage(message_id="msg-1", thread_id="t1", subject="Sale")
    store = DecisionStore(db_path=tmp_path / "decisions.db")
    agent = GmailAgent(service=MagicMock(), mode="dry_run", store=store)

    with patch("app.agent.classify", return_value=_decision()):
        result = agent.process_email(email)

    assert store.has_message("msg-1") is True
    row = store.get_decision("msg-1")
    assert row is not None
    assert "dry_run" in result.execution_note
    assert row["execution_note"] == result.execution_note

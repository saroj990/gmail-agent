"""Gmail action execution gates and Lesson 5 label writes."""

from __future__ import annotations

from googleapiclient.discovery import Resource

from app.config import GMAIL_LABEL, MODE
from app.gmail import apply_label, ensure_label
from app.models import Action, ClassificationResult


def gmail_writes_allowed(mode: str | None = None) -> bool:
    """Return True only when the runtime mode permits Gmail mutations."""
    current = (mode or MODE).strip().lower()
    return current in {"approval", "automatic"}


def proposed_action(decision: ClassificationResult) -> Action:
    """Return the action the agent proposes (never executes by itself)."""
    return decision.action


def apply_to_process_label(
    service: Resource,
    message_id: str,
    *,
    label_name: str | None = None,
) -> str:
    """Ensure the target label exists and apply it to one message (no archive)."""
    name = label_name or GMAIL_LABEL
    label_id = ensure_label(service, name)
    apply_label(service, message_id, label_id)
    return name


def execute_decision(
    decision: ClassificationResult,
    *,
    mode: str | None = None,
    service: Resource | None = None,
    message_id: str | None = None,
) -> str:
    """Execute or skip a decision based on MODE.

    Lesson 5: LABEL_AND_ARCHIVE applies the label only (archive comes in Lesson 6).
    """
    action = proposed_action(decision)
    current_mode = mode or MODE

    if not gmail_writes_allowed(current_mode):
        return f"skipped ({current_mode}): {action.value}"

    if action in {Action.LEAVE_IN_INBOX, Action.NO_ACTION}:
        return f"no write: {action.value}"

    if action == Action.LABEL_AND_ARCHIVE:
        if service is None or not message_id:
            raise ValueError("service and message_id are required to apply labels")
        label_name = apply_to_process_label(service, message_id)
        return f"applied label: {label_name} (archive deferred to Lesson 6)"

    raise NotImplementedError(f"Unsupported action: {action.value}")

"""Gmail action execution gates, labels, and archive."""

from __future__ import annotations

from googleapiclient.discovery import Resource

from app.config import CONFIDENCE_THRESHOLD, GMAIL_LABEL, MODE
from app.gmail import apply_label, archive_message, ensure_label
from app.models import Action, Category, ClassificationResult


def gmail_writes_allowed(mode: str | None = None) -> bool:
    """Return True only when the runtime mode permits Gmail mutations."""
    current = (mode or MODE).strip().lower()
    return current in {"approval", "automatic"}


def proposed_action(decision: ClassificationResult) -> Action:
    """Return the action the agent proposes (never executes by itself)."""
    return decision.action


def meets_archive_guards(
    decision: ClassificationResult,
    *,
    mode: str | None = None,
    threshold: float | None = None,
) -> tuple[bool, str]:
    """Return whether label+archive is allowed, plus a reason string."""
    current_mode = mode or MODE
    min_confidence = CONFIDENCE_THRESHOLD if threshold is None else threshold

    if not gmail_writes_allowed(current_mode):
        return False, f"mode is {current_mode}"

    if decision.category != Category.TO_PROCESS:
        return False, f"category is {decision.category.value}"

    if decision.confidence < min_confidence:
        return False, f"confidence {decision.confidence:.2f} < {min_confidence:.2f}"

    return True, "ok"


def apply_to_process_label(
    service: Resource,
    message_id: str,
    *,
    label_name: str | None = None,
) -> str:
    """Ensure the target label exists and apply it to one message."""
    name = label_name or GMAIL_LABEL
    label_id = ensure_label(service, name)
    apply_label(service, message_id, label_id)
    return name


def label_and_archive(
    service: Resource,
    message_id: str,
    *,
    label_name: str | None = None,
) -> str:
    """Apply To Process label and archive by removing INBOX."""
    name = apply_to_process_label(service, message_id, label_name=label_name)
    archive_message(service, message_id)
    return name


def execute_decision(
    decision: ClassificationResult,
    *,
    mode: str | None = None,
    service: Resource | None = None,
    message_id: str | None = None,
) -> str:
    """Execute or skip a decision based on MODE and safety guards."""
    action = proposed_action(decision)
    current_mode = mode or MODE

    if not gmail_writes_allowed(current_mode):
        return f"skipped ({current_mode}): {action.value}"

    if action in {Action.LEAVE_IN_INBOX, Action.NO_ACTION}:
        return f"no write: {action.value}"

    if action == Action.LABEL_AND_ARCHIVE:
        allowed, reason = meets_archive_guards(decision, mode=current_mode)
        if not allowed:
            return f"skipped ({reason}): {action.value}"

        if service is None or not message_id:
            raise ValueError("service and message_id are required to label/archive")

        label_name = label_and_archive(service, message_id)
        return f"labeled '{label_name}' and archived"

    raise NotImplementedError(f"Unsupported action: {action.value}")

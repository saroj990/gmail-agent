"""Gmail action execution gates.

Lesson 4: dry_run never mutates Gmail.
Later lessons will implement label/archive behind these checks.
"""

from __future__ import annotations

from app.config import MODE
from app.models import Action, ClassificationResult


def gmail_writes_allowed(mode: str | None = None) -> bool:
    """Return True only when the runtime mode permits Gmail mutations."""
    current = (mode or MODE).strip().lower()
    return current in {"approval", "automatic"}


def proposed_action(decision: ClassificationResult) -> Action:
    """Return the action the agent proposes (never executes by itself)."""
    return decision.action


def execute_decision(
    decision: ClassificationResult,
    *,
    mode: str | None = None,
) -> str:
    """Execute or skip a decision based on MODE.

    In dry_run, always skip. Real Gmail writes come in later lessons.
    """
    action = proposed_action(decision)
    if not gmail_writes_allowed(mode):
        return f"skipped ({mode or MODE}): {action.value}"

    # Lessons 5–6 will implement LABEL_AND_ARCHIVE here.
    raise NotImplementedError(
        f"Gmail mutation for {action.value} is not implemented yet. "
        "Stay on MODE=dry_run until Lessons 5–6."
    )

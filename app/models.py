"""Shared Pydantic models for parsed mail and LLM decisions.

The classifier must return ClassificationResult. Category always drives Action
so the model cannot invent DELETE or a mismatched action.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EmailMessage(BaseModel):
    """Normalized email extracted from a Gmail API MIME message."""

    message_id: str
    thread_id: str
    sender: str = ""
    recipient: str = ""
    subject: str = ""
    date: str = ""
    body: str = ""
    snippet: str = ""


class Category(str, Enum):
    """How much attention this email likely needs."""

    IMPORTANT = "IMPORTANT"  # keep in Inbox
    TO_PROCESS = "TO_PROCESS"  # low-value; label + archive when allowed
    UNKNOWN = "UNKNOWN"  # not confident; do nothing


class Importance(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Action(str, Enum):
    """What deterministic code may do after classification. No delete/send."""

    LEAVE_IN_INBOX = "LEAVE_IN_INBOX"
    LABEL_AND_ARCHIVE = "LABEL_AND_ARCHIVE"
    NO_ACTION = "NO_ACTION"


# If the model names these, we treat the output as invalid / UNKNOWN.
FORBIDDEN_ACTIONS = frozenset({"DELETE", "MOVE_TO_SPAM"})


class ClassificationResult(BaseModel):
    """Structured classification decision from the local LLM."""

    category: Category
    importance: Importance
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    action: Action

    @model_validator(mode="after")
    def align_action_with_category(self) -> ClassificationResult:
        # Deterministic mapping: code, not the LLM, owns the final action.
        expected = {
            Category.IMPORTANT: Action.LEAVE_IN_INBOX,
            Category.TO_PROCESS: Action.LABEL_AND_ARCHIVE,
            Category.UNKNOWN: Action.NO_ACTION,
        }[self.category]
        if self.action != expected:
            self.action = expected
        return self

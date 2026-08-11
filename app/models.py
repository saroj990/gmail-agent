"""Shared Pydantic models."""

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
    IMPORTANT = "IMPORTANT"
    TO_PROCESS = "TO_PROCESS"
    UNKNOWN = "UNKNOWN"


class Importance(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Action(str, Enum):
    LEAVE_IN_INBOX = "LEAVE_IN_INBOX"
    LABEL_AND_ARCHIVE = "LABEL_AND_ARCHIVE"
    NO_ACTION = "NO_ACTION"


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
        expected = {
            Category.IMPORTANT: Action.LEAVE_IN_INBOX,
            Category.TO_PROCESS: Action.LABEL_AND_ARCHIVE,
            Category.UNKNOWN: Action.NO_ACTION,
        }[self.category]
        if self.action != expected:
            self.action = expected
        return self

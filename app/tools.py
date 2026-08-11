"""Allowlisted Gmail tools for the agent (Lesson 8).

The model/agent may only request tools in ALLOWED_TOOLS.
Forbidden operations (delete/send/reply/spam) have no tool and are rejected.
"""

from __future__ import annotations

from typing import Any, Callable

from googleapiclient.discovery import Resource

from app.actions import apply_to_process_label
from app.config import GMAIL_LABEL, MAX_EMAILS_PER_RUN
from app.gmail import archive_message, get_message, get_service, list_messages
from app.models import EmailMessage
from app.parser import parse

ALLOWED_TOOLS = frozenset(
    {
        "get_recent_emails",
        "read_email",
        "apply_label",
        "archive_email",
    }
)

# Explicit denylist so invented names cannot sneak through as "helpful" extras.
FORBIDDEN_TOOLS = frozenset(
    {
        "delete",
        "delete_email",
        "send",
        "send_email",
        "reply",
        "reply_email",
        "forward",
        "move_to_spam",
        "spam",
        "trash",  # review CLI may trash; agent tools do not
        "trash_email",
    }
)


class ToolError(Exception):
    """Raised when a tool name is unknown or forbidden."""


class GmailTools:
    """Controlled interface over Gmail operations the agent may use."""

    def __init__(self, service: Resource | None = None) -> None:
        self.service = service

    def _ensure_service(self) -> Resource:
        if self.service is None:
            self.service = get_service()
        return self.service

    def get_recent_emails(self, max_results: int | None = None) -> list[dict[str, Any]]:
        """Return recent message stubs: [{id, threadId}, ...]."""
        limit = MAX_EMAILS_PER_RUN if max_results is None else max_results
        return list_messages(self._ensure_service(), max_results=limit)

    def read_email(self, message_id: str) -> EmailMessage:
        """Fetch and parse one email by id."""
        raw = get_message(self._ensure_service(), message_id)
        return parse(raw)

    def apply_label(self, message_id: str, label_name: str | None = None) -> str:
        """Apply the configured (or given) label to a message."""
        return apply_to_process_label(
            self._ensure_service(),
            message_id,
            label_name=label_name or GMAIL_LABEL,
        )

    def archive_email(self, message_id: str) -> str:
        """Archive a message by removing INBOX."""
        archive_message(self._ensure_service(), message_id)
        return message_id

    def _handlers(self) -> dict[str, Callable[..., Any]]:
        return {
            "get_recent_emails": self.get_recent_emails,
            "read_email": self.read_email,
            "apply_label": self.apply_label,
            "archive_email": self.archive_email,
        }

    def invoke(self, tool_name: str, **kwargs: Any) -> Any:
        """Call an allowlisted tool by name. Reject unknown/forbidden tools."""
        name = tool_name.strip()
        if name in FORBIDDEN_TOOLS:
            raise ToolError(f"Forbidden tool: {name}")
        if name not in ALLOWED_TOOLS:
            raise ToolError(
                f"Unknown tool: {name}. Allowed: {sorted(ALLOWED_TOOLS)}"
            )
        return self._handlers()[name](**kwargs)

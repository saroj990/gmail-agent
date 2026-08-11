"""Shared Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


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

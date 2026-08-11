"""Gmail API client (read-only OAuth)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from app.config import CREDENTIALS_PATH, GMAIL_SCOPES, TOKEN_PATH


class GmailAuthError(Exception):
    """Raised when OAuth credentials or tokens cannot be loaded."""


def get_service(
    credentials_path: Path | None = None,
    token_path: Path | None = None,
    scopes: tuple[str, ...] | None = None,
) -> Resource:
    """Authenticate with Google OAuth and return a Gmail API service."""
    credentials_path = credentials_path or CREDENTIALS_PATH
    token_path = token_path or TOKEN_PATH
    scopes = scopes or GMAIL_SCOPES

    if not credentials_path.exists():
        raise GmailAuthError(
            f"Missing OAuth client file: {credentials_path}. "
            "Download Desktop credentials from Google Cloud and save as credentials.json."
        )

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), list(scopes))

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), list(scopes)
            )
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_messages(
    service: Resource,
    *,
    max_results: int = 10,
    query: str | None = None,
    user_id: str = "me",
) -> list[dict[str, Any]]:
    """List message stubs (id, threadId) for the mailbox."""
    kwargs: dict[str, Any] = {
        "userId": user_id,
        "maxResults": max_results,
    }
    if query:
        kwargs["q"] = query

    response = service.users().messages().list(**kwargs).execute()
    return response.get("messages", [])


def get_message(
    service: Resource,
    message_id: str,
    *,
    user_id: str = "me",
    format: str = "full",
) -> dict[str, Any]:
    """Fetch a single Gmail message by id."""
    return (
        service.users()
        .messages()
        .get(userId=user_id, id=message_id, format=format)
        .execute()
    )


def get_header(message: dict[str, Any], name: str) -> str:
    """Return a header value from a Gmail message payload (case-insensitive)."""
    headers = message.get("payload", {}).get("headers", [])
    target = name.lower()
    for header in headers:
        if header.get("name", "").lower() == target:
            return header.get("value", "")
    return ""


def summarize_message(message: dict[str, Any]) -> dict[str, str]:
    """Extract display fields used by Lesson 1 output."""
    return {
        "from": get_header(message, "From"),
        "subject": get_header(message, "Subject"),
        "date": get_header(message, "Date"),
        "snippet": message.get("snippet", ""),
    }

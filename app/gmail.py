"""Gmail API client: OAuth, read messages, labels, archive, trash.

Archive = remove the INBOX label. Trash is recoverable. There is no permanent
delete helper here on purpose.
"""

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


def _scopes_granted(creds: Credentials, scopes: tuple[str, ...]) -> bool:
    granted = set(creds.scopes or [])
    return set(scopes).issubset(granted)


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
        if creds and not _scopes_granted(creds, scopes):
            # Old token was likely readonly-only; force a fresh consent for modify scopes.
            creds = None

    if not creds or not creds.valid:
        # Refresh quietly when possible; otherwise open a browser login.
        if creds and creds.expired and creds.refresh_token and _scopes_granted(creds, scopes):
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


def list_labels(service: Resource, *, user_id: str = "me") -> list[dict[str, Any]]:
    """Return all labels in the mailbox."""
    response = service.users().labels().list(userId=user_id).execute()
    return response.get("labels", [])


def get_label_id(
    service: Resource,
    name: str,
    *,
    user_id: str = "me",
) -> str | None:
    """Return the label id for an exact label name, or None if missing."""
    for label in list_labels(service, user_id=user_id):
        if label.get("name") == name:
            return label.get("id")
    return None


def create_label(
    service: Resource,
    name: str,
    *,
    user_id: str = "me",
) -> str:
    """Create a user label and return its id."""
    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId=user_id, body=body).execute()
    label_id = created.get("id")
    if not label_id:
        raise RuntimeError(f"Gmail did not return an id for label {name!r}")
    return label_id


def ensure_label(
    service: Resource,
    name: str,
    *,
    user_id: str = "me",
) -> str:
    """Get an existing label id or create the label if it does not exist."""
    existing = get_label_id(service, name, user_id=user_id)
    if existing:
        return existing
    return create_label(service, name, user_id=user_id)


def apply_label(
    service: Resource,
    message_id: str,
    label_id: str,
    *,
    user_id: str = "me",
) -> dict[str, Any]:
    """Apply a label to a message. Does not archive or delete."""
    return (
        service.users()
        .messages()
        .modify(
            userId=user_id,
            id=message_id,
            body={"addLabelIds": [label_id]},
        )
        .execute()
    )


def archive_message(
    service: Resource,
    message_id: str,
    *,
    user_id: str = "me",
) -> dict[str, Any]:
    """Archive a message by removing the INBOX label."""
    return (
        service.users()
        .messages()
        .modify(
            userId=user_id,
            id=message_id,
            body={"removeLabelIds": ["INBOX"]},
        )
        .execute()
    )


def trash_message(
    service: Resource,
    message_id: str,
    *,
    user_id: str = "me",
) -> dict[str, Any]:
    """Move a message to Trash (recoverable). Never permanently deletes."""
    return service.users().messages().trash(userId=user_id, id=message_id).execute()

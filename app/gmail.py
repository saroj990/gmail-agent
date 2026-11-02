"""Gmail API client: OAuth, read messages, labels, archive, trash.

Archive = remove the INBOX label. Trash is recoverable. There is no permanent
delete helper here on purpose.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from app.config import CREDENTIALS_PATH, GMAIL_SCOPES, TOKEN_PATH


class GmailAuthError(Exception):
    """Raised when OAuth credentials or tokens cannot be loaded."""


class GmailNotSignedInError(GmailAuthError):
    """Raised by non-interactive get_service() when no usable login is saved."""


def _scopes_granted(creds: Credentials, scopes: tuple[str, ...]) -> bool:
    granted = set(creds.scopes or [])
    return set(scopes).issubset(granted)


def _refresh_credentials(creds: Credentials, token_path: Path) -> None:
    """Refresh an expired access token, converting Google errors to GmailAuthError."""
    try:
        creds.refresh(Request())
    except RefreshError as exc:
        # invalid_grant: refresh token expired (7-day limit for OAuth apps in
        # Testing status), revoked, or issued for a different OAuth client.
        raise GmailAuthError(
            "Saved Gmail login is no longer valid (Google rejected the refresh token). "
            f"Sign in again: delete {token_path} and rerun the command, or use "
            "'Sign in with Google' in the web UI. If this repeats weekly, set the "
            "OAuth consent screen to 'In production' in Google Cloud Console."
        ) from exc
    except TransportError as exc:
        raise GmailAuthError(
            "Could not reach Google to refresh the Gmail login. Check your network connection."
        ) from exc


def _require_client_file(credentials_path: Path) -> None:
    if not credentials_path.exists():
        raise GmailAuthError(
            f"Missing OAuth client file: {credentials_path}. "
            "Download Desktop credentials from Google Cloud and save as credentials.json."
        )


def run_login_flow(
    credentials_path: Path | None = None,
    token_path: Path | None = None,
    scopes: tuple[str, ...] | None = None,
    *,
    timeout_seconds: int | None = None,
) -> Credentials:
    """Open the Google consent page in a browser and save the resulting token."""
    credentials_path = credentials_path or CREDENTIALS_PATH
    token_path = token_path or TOKEN_PATH
    scopes = scopes or GMAIL_SCOPES
    _require_client_file(credentials_path)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), list(scopes))
    try:
        creds = flow.run_local_server(port=0, timeout_seconds=timeout_seconds)
    except Exception as exc:
        # Timeouts and denied consent surface as assorted oauthlib/requests errors.
        raise GmailAuthError(
            "Google sign-in did not complete (the consent page was closed, denied, "
            "or timed out). Try again."
        ) from exc

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_service(
    credentials_path: Path | None = None,
    token_path: Path | None = None,
    scopes: tuple[str, ...] | None = None,
    *,
    interactive: bool = True,
) -> Resource:
    """Authenticate with Google OAuth and return a Gmail API service.

    With interactive=False a missing/unusable token raises GmailAuthError
    instead of opening a browser (used by the web server).
    """
    credentials_path = credentials_path or CREDENTIALS_PATH
    token_path = token_path or TOKEN_PATH
    scopes = scopes or GMAIL_SCOPES
    _require_client_file(credentials_path)

    creds: Credentials | None = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), list(scopes))
        except ValueError as exc:
            raise GmailAuthError(
                f"Saved Gmail login in {token_path} is unreadable. Sign in again."
            ) from exc
        if creds and not _scopes_granted(creds, scopes):
            # Old token was likely readonly-only; force a fresh consent for modify scopes.
            creds = None

    if not creds or not creds.valid:
        # Refresh quietly when possible; otherwise open a browser login.
        if creds and creds.expired and creds.refresh_token and _scopes_granted(creds, scopes):
            _refresh_credentials(creds, token_path)
            token_path.write_text(creds.to_json(), encoding="utf-8")
        elif interactive:
            creds = run_login_flow(credentials_path, token_path, scopes)
        else:
            raise GmailNotSignedInError("Not signed in to Gmail. Sign in with Google first.")

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def sign_out(token_path: Path | None = None) -> None:
    """Forget the saved login by deleting the local token file."""
    (token_path or TOKEN_PATH).unlink(missing_ok=True)


def get_profile_email(service: Resource, *, user_id: str = "me") -> str:
    """Return the signed-in mailbox address."""
    profile = service.users().getProfile(userId=user_id).execute()
    return str(profile.get("emailAddress", ""))


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

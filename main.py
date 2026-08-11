"""Entrypoint: fetch, parse, and print recent Gmail messages (read-only)."""

from __future__ import annotations

from app.config import MAX_EMAILS_PER_RUN
from app.gmail import GmailAuthError, get_message, get_service, list_messages
from app.models import EmailMessage
from app.parser import parse


def fetch_recent_emails(max_results: int = MAX_EMAILS_PER_RUN) -> list[EmailMessage]:
    """Authenticate, fetch recent messages, and return parsed EmailMessage models."""
    service = get_service()
    stubs = list_messages(service, max_results=max_results)

    emails: list[EmailMessage] = []
    for stub in stubs:
        raw = get_message(service, stub["id"])
        emails.append(parse(raw))
    return emails


def print_emails(emails: list[EmailMessage]) -> None:
    """Print parsed emails in a readable Lesson 2 format."""
    print(f"Found {len(emails)} emails\n")

    for index, email in enumerate(emails, start=1):
        body_preview = email.body.replace("\n", " ").strip()
        if len(body_preview) > 160:
            body_preview = body_preview[:157] + "..."

        print(f"{index}.")
        print(f"From: {email.sender}")
        print(f"To: {email.recipient}")
        print(f"Subject: {email.subject}")
        print(f"Date: {email.date}")
        print(f"Snippet: {email.snippet}")
        print(f"Body: {body_preview}")
        print()


def main() -> None:
    try:
        emails = fetch_recent_emails()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print_emails(emails)


if __name__ == "__main__":
    main()

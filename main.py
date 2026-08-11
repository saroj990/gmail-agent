"""Entrypoint: fetch, parse, and classify recent Gmail messages (read-only)."""

from __future__ import annotations

from app.classifier import ClassifierError, classify
from app.config import MAX_EMAILS_PER_RUN
from app.gmail import GmailAuthError, get_message, get_service, list_messages
from app.models import ClassificationResult, EmailMessage
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


def print_classification(index: int, email: EmailMessage, decision: ClassificationResult) -> None:
    """Print one email and its classification decision."""
    print(f"[{index}]")
    print(f"From: {email.sender}")
    print(f"Subject: {email.subject}")
    print()
    print(f"Category: {decision.category.value}")
    print(f"Importance: {decision.importance.value}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Action: {decision.action.value}")
    print(f"Reason: {decision.reason}")
    print()


def main() -> None:
    try:
        emails = fetch_recent_emails()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print(f"Classifying {len(emails)} emails...\n")

    try:
        for index, email in enumerate(emails, start=1):
            decision = classify(email)
            print_classification(index, email, decision)
    except ClassifierError as exc:
        print(f"Classifier error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

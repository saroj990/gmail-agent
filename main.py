"""Entrypoint: dry-run pipeline — fetch → parse → classify → report (no Gmail writes)."""

from __future__ import annotations

from app.actions import execute_decision
from app.classifier import ClassifierError, classify
from app.config import MAX_EMAILS_PER_RUN, MODE
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


def print_classification(
    index: int,
    email: EmailMessage,
    decision: ClassificationResult,
    execution_note: str,
) -> None:
    """Print one email, its classification, and dry-run execution status."""
    print(f"[{index}]")
    print(f"From: {email.sender}")
    print(f"Subject: {email.subject}")
    print()
    print(f"Category: {decision.category.value}")
    print(f"Importance: {decision.importance.value}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Action: {decision.action.value}")
    print(f"Reason: {decision.reason}")
    print(f"Execution: {execution_note}")
    print()


def main() -> None:
    print(f"MODE={MODE}")
    if MODE == "dry_run":
        print("Dry run enabled — classifications only; Gmail will not be modified.\n")

    try:
        emails = fetch_recent_emails()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print(f"Analyzing {len(emails)} emails...\n")

    try:
        for index, email in enumerate(emails, start=1):
            decision = classify(email)
            execution_note = execute_decision(decision)
            print_classification(index, email, decision, execution_note)
    except ClassifierError as exc:
        print(f"Classifier error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

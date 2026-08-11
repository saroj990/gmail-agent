"""Entrypoint: classify pipeline + Lesson 5 label helpers."""

from __future__ import annotations

import argparse

from app.actions import apply_to_process_label, execute_decision, gmail_writes_allowed
from app.classifier import ClassifierError, classify
from app.config import GMAIL_LABEL, MAX_EMAILS_PER_RUN, MODE
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
    """Print one email, its classification, and execution status."""
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


def run_pipeline() -> None:
    print(f"MODE={MODE}")
    if MODE == "dry_run":
        print("Dry run enabled — classifications only; Gmail will not be modified.\n")

    try:
        service = get_service()
        stubs = list_messages(service, max_results=MAX_EMAILS_PER_RUN)
        emails: list[EmailMessage] = []
        for stub in stubs:
            emails.append(parse(get_message(service, stub["id"])))
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print(f"Analyzing {len(emails)} emails...\n")

    try:
        for index, (stub, email) in enumerate(zip(stubs, emails, strict=True), start=1):
            decision = classify(email)
            execution_note = execute_decision(
                decision,
                service=service,
                message_id=stub["id"],
            )
            print_classification(index, email, decision, execution_note)
    except ClassifierError as exc:
        print(f"Classifier error: {exc}")
        raise SystemExit(1) from exc


def cmd_ensure_label() -> None:
    """Create or fetch the configured Gmail label."""
    try:
        service = get_service()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    from app.gmail import ensure_label

    label_id = ensure_label(service, GMAIL_LABEL)
    print(f"Label ready: {GMAIL_LABEL!r} (id={label_id})")


def cmd_apply_label(message_id: str) -> None:
    """Apply the To Process label to one message (no archive)."""
    if not gmail_writes_allowed():
        print(
            f"Refusing to label in MODE={MODE}. "
            "Set MODE=approval or MODE=automatic for a single test apply."
        )
        raise SystemExit(1)

    try:
        service = get_service()
        label_name = apply_to_process_label(service, message_id)
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print(f"Applied label {label_name!r} to message {message_id}")
    print("Note: message was NOT archived (Lesson 6).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gmail AI Inbox Agent")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("ensure-label", help=f"Create/get the {GMAIL_LABEL!r} label")

    apply = sub.add_parser(
        "apply-label",
        help="Apply To Process label to one message id (requires MODE!=dry_run)",
    )
    apply.add_argument("message_id", help="Gmail message id")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ensure-label":
        cmd_ensure_label()
        return
    if args.command == "apply-label":
        cmd_apply_label(args.message_id)
        return

    run_pipeline()


if __name__ == "__main__":
    main()

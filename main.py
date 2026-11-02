"""CLI entrypoint for the Gmail AI Inbox Agent.

Default command (`python main.py`) runs the agent pipeline:
Fetch → Parse → Classify → Validate → Decide → Execute.

Subcommands are for one-off Gmail operations (label, archive, interactive review).
MODE from config/.env controls whether Execute may change Gmail:
  dry_run   — classify and print only (default)
  approval  — ask y/N before label+archive
  automatic — label+archive when confidence guards pass
"""

from __future__ import annotations

import argparse

from app.actions import apply_to_process_label, gmail_writes_allowed, label_and_archive
from app.agent import AgentResult, GmailAgent, run_agent
from app.classifier import ClassifierError
from app.config import CONFIDENCE_THRESHOLD, GMAIL_LABEL, MAX_EMAILS_PER_RUN, MODE
from app.gmail import GmailAuthError, archive_message, ensure_label, get_service
from app.models import EmailMessage
from app.review import run_review


def fetch_recent_emails(max_results: int = MAX_EMAILS_PER_RUN) -> list[EmailMessage]:
    """Fetch and parse recent emails via allowlisted tools (no classify/execute)."""
    agent = GmailAgent(max_emails=max_results)
    return agent.fetch_emails()


def print_classification(index: int, result: AgentResult) -> None:
    """Print one classified email and whether Gmail was changed."""
    email, decision = result.email, result.decision
    print(f"[{index}]")
    print(f"Message-ID: {email.message_id}")
    print(f"From: {email.sender}")
    print(f"Subject: {email.subject}")
    print()
    print(f"Category: {decision.category.value}")
    print(f"Importance: {decision.importance.value}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Action: {result.action.value}")
    print(f"Reason: {decision.reason}")
    print(f"Execution: {result.execution_note}")
    print()


def run_pipeline() -> None:
    """Default path: run the agent over recent unprocessed emails."""
    print(f"MODE={MODE}")
    print(f"CONFIDENCE_THRESHOLD={CONFIDENCE_THRESHOLD}")
    if MODE == "dry_run":
        print("Dry run enabled — classifications only; Gmail will not be modified.\n")
    elif MODE == "approval":
        print("Approval mode — you will be asked [y/N] before each archive.\n")
    elif MODE == "automatic":
        print("Automatic mode — high-confidence TO_PROCESS mail may be labeled/archived.\n")

    try:
        results = run_agent()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc
    except ClassifierError as exc:
        print(f"Classifier error: {exc}")
        raise SystemExit(1) from exc

    print(f"Analyzing {len(results)} emails...\n")
    for index, result in enumerate(results, start=1):
        print_classification(index, result)


def cmd_ensure_label() -> None:
    """Create or fetch the configured Gmail label (usually 'To Process')."""
    try:
        service = get_service()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    label_id = ensure_label(service, GMAIL_LABEL)
    print(f"Label ready: {GMAIL_LABEL!r} (id={label_id})")


def cmd_apply_label(message_id: str) -> None:
    """Apply the To Process label to one message. Does not archive."""
    # Manual writes are blocked in dry_run so a test apply cannot happen by accident.
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
    print("Note: message was NOT archived. Use label-and-archive to archive.")


def cmd_archive(message_id: str) -> None:
    """Remove INBOX from one message (archive). Does not add a label."""
    if not gmail_writes_allowed():
        print(
            f"Refusing to archive in MODE={MODE}. "
            "Set MODE=approval or MODE=automatic for a single test archive."
        )
        raise SystemExit(1)

    try:
        service = get_service()
        archive_message(service, message_id)
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print(f"Archived message {message_id} (removed INBOX label)")


def cmd_label_and_archive(message_id: str) -> None:
    """Apply To Process and archive one message (typical TO_PROCESS action)."""
    if not gmail_writes_allowed():
        print(
            f"Refusing to label/archive in MODE={MODE}. "
            "Set MODE=approval or MODE=automatic first."
        )
        raise SystemExit(1)

    try:
        service = get_service()
        label_name = label_and_archive(service, message_id)
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print(f"Labeled {label_name!r} and archived message {message_id}")


def cmd_review() -> None:
    """Interactive flow: classify all fetched mail, then approve archive/trash."""
    try:
        service = get_service()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    try:
        run_review(service)
    except ClassifierError as exc:
        print(f"Classifier error: {exc}")
        raise SystemExit(1) from exc


def cmd_serve(port: int) -> None:
    """Start the local web UI + API on 127.0.0.1."""
    import uvicorn

    print(f"Web UI: http://localhost:{port}")
    uvicorn.run("app.server:create_app", factory=True, host="127.0.0.1", port=port)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI: no subcommand = agent pipeline; named commands = helpers."""
    parser = argparse.ArgumentParser(description="Gmail AI Inbox Agent")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start the local web UI on 127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    sub.add_parser(
        "review",
        help="Dry-run all emails, show summary, then approve archive/trash one by one",
    )

    sub.add_parser("ensure-label", help=f"Create/get the {GMAIL_LABEL!r} label")

    apply = sub.add_parser(
        "apply-label",
        help="Apply To Process label to one message id (requires MODE!=dry_run)",
    )
    apply.add_argument("message_id", help="Gmail message id")

    archive = sub.add_parser(
        "archive",
        help="Archive one message by removing INBOX (requires MODE!=dry_run)",
    )
    archive.add_argument("message_id", help="Gmail message id")

    both = sub.add_parser(
        "label-and-archive",
        help="Label To Process + archive one message (requires MODE!=dry_run)",
    )
    both.add_argument("message_id", help="Gmail message id")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Dispatch a subcommand, or run the default agent pipeline."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        cmd_serve(args.port)
        return
    if args.command == "review":
        cmd_review()
        return
    if args.command == "ensure-label":
        cmd_ensure_label()
        return
    if args.command == "apply-label":
        cmd_apply_label(args.message_id)
        return
    if args.command == "archive":
        cmd_archive(args.message_id)
        return
    if args.command == "label-and-archive":
        cmd_label_and_archive(args.message_id)
        return

    # python main.py with no subcommand
    run_pipeline()


if __name__ == "__main__":
    main()

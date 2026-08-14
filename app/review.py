"""Interactive review: always dry-run first, then ask before any Gmail write."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from googleapiclient.discovery import Resource

from app.actions import label_and_archive
from app.classifier import classify
from app.config import CONFIDENCE_THRESHOLD, GMAIL_LABEL, MAX_EMAILS_PER_RUN
from app.database import DecisionStore
from app.gmail import get_message, list_messages, trash_message
from app.models import Category, ClassificationResult, EmailMessage
from app.parser import parse


@dataclass
class ReviewItem:
    email: EmailMessage
    decision: ClassificationResult


def classify_batch(
    service: Resource,
    *,
    max_results: int = MAX_EMAILS_PER_RUN,
    store: DecisionStore | None = None,
) -> list[ReviewItem]:
    """Fetch, parse, and classify emails with zero Gmail writes.

    Skips message_ids already present in SQLite memory.
    """
    memory = store or DecisionStore()
    stubs = list_messages(service, max_results=max_results)
    items: list[ReviewItem] = []
    skipped = 0
    for stub in stubs:
        if memory.has_message(stub["id"]):
            skipped += 1
            continue
        email = parse(get_message(service, stub["id"]))
        decision = classify(email)
        memory.save_decision(
            email,
            decision,
            action=decision.action.value,
            execution_note="review dry-run classified",
        )
        items.append(ReviewItem(email=email, decision=decision))
    if skipped:
        print(f"Skipping {skipped} already-processed email(s) from memory.\n")
    return items


def summarize(items: list[ReviewItem], *, threshold: float = CONFIDENCE_THRESHOLD) -> dict[str, int]:
    """Return category counts and how many are archive candidates."""
    summary = {
        "total": len(items),
        "IMPORTANT": 0,
        "TO_PROCESS": 0,
        "UNKNOWN": 0,
        "archive_candidates": 0,
    }
    for item in items:
        summary[item.decision.category.value] += 1
        if (
            item.decision.category == Category.TO_PROCESS
            and item.decision.confidence >= threshold
        ):
            summary["archive_candidates"] += 1
    return summary


def print_dry_run(items: list[ReviewItem]) -> None:
    """Print each classification (dry-run style)."""
    print(f"Dry-run classifying {len(items)} emails...\n")
    for index, item in enumerate(items, start=1):
        email, decision = item.email, item.decision
        print(f"[{index}]")
        print(f"Message-ID: {email.message_id}")
        print(f"From: {email.sender}")
        print(f"Subject: {email.subject}")
        print(f"Category: {decision.category.value}")
        print(f"Importance: {decision.importance.value}")
        print(f"Confidence: {decision.confidence:.2f}")
        print(f"Action: {decision.action.value}")
        print(f"Reason: {decision.reason}")
        print()


def print_summary(summary: dict[str, int], *, threshold: float) -> None:
    """Print a short rollup after dry-run."""
    print("=" * 40)
    print("SUMMARY")
    print("=" * 40)
    print(f"Total analyzed:        {summary['total']}")
    print(f"IMPORTANT:             {summary['IMPORTANT']}")
    print(f"TO_PROCESS:            {summary['TO_PROCESS']}")
    print(f"UNKNOWN:               {summary['UNKNOWN']}")
    print(
        f"Archive candidates:    {summary['archive_candidates']} "
        f"(TO_PROCESS and confidence >= {threshold:.2f})"
    )
    print("=" * 40)
    print()


def archive_candidates(
    items: list[ReviewItem],
    *,
    threshold: float = CONFIDENCE_THRESHOLD,
) -> list[ReviewItem]:
    """Items proposed for label+archive under the confidence threshold."""
    return [
        item
        for item in items
        if item.decision.category == Category.TO_PROCESS
        and item.decision.confidence >= threshold
    ]


def prompt_choice(prompt: str, input_fn: Callable[[str], str] = input) -> str:
    return input_fn(prompt).strip().lower()


def run_review(
    service: Resource,
    *,
    max_results: int = MAX_EMAILS_PER_RUN,
    threshold: float = CONFIDENCE_THRESHOLD,
    input_fn: Callable[[str], str] = input,
    store: DecisionStore | None = None,
    db_path: Path | None = None,
) -> None:
    """Always dry-run, show summary, then ask before archive or trash."""
    memory = store or DecisionStore(db_path=db_path)
    print("REVIEW MODE")
    print("Phase 1: dry-run only (no Gmail changes)\n")

    items = classify_batch(service, max_results=max_results, store=memory)
    print_dry_run(items)

    summary = summarize(items, threshold=threshold)
    print_summary(summary, threshold=threshold)

    candidates = archive_candidates(items, threshold=threshold)
    if not candidates:
        print("No archive candidates. Done.")
        return

    print("Phase 2: approvals")
    print("Permanent delete is NOT offered.")
    print("Options per email: [a]rchive  [t]rash  [s]kip  [q]uit")
    print("Trash = move to Gmail Trash (recoverable for ~30 days).\n")

    archived = 0
    trashed = 0
    skipped = 0

    for index, item in enumerate(candidates, start=1):
        email, decision = item.email, item.decision
        print("-" * 40)
        print(f"Candidate {index}/{len(candidates)}")
        print(f"Message-ID: {email.message_id}")
        print(f"From: {email.sender}")
        print(f"Subject: {email.subject}")
        print(f"Confidence: {decision.confidence:.2f}")
        print(f"Reason: {decision.reason}")

        while True:
            # Trash requires typing "trash" so a stray Enter cannot delete from Inbox.
            choice = prompt_choice("[a]rchive / [t]rash / [s]kip / [q]uit: ", input_fn)
            if choice in {"a", "archive"}:
                label_and_archive(service, email.message_id)
                note = f"labeled '{GMAIL_LABEL}' and archived"
                memory.save_decision(email, decision, execution_note=note)
                print(f"→ Labeled '{GMAIL_LABEL}' and archived.")
                archived += 1
                break
            if choice in {"t", "trash"}:
                confirm = prompt_choice(
                    "Confirm move to Trash? type 'trash' to confirm: ",
                    input_fn,
                )
                if confirm == "trash":
                    trash_message(service, email.message_id)
                    memory.save_decision(
                        email,
                        decision,
                        execution_note="moved to trash",
                    )
                    print("→ Moved to Trash.")
                    trashed += 1
                    break
                print("Trash cancelled.")
                continue
            if choice in {"s", "skip", "n", ""}:
                memory.save_decision(
                    email,
                    decision,
                    execution_note="review skipped by user",
                )
                print("→ Skipped.")
                skipped += 1
                break
            if choice in {"q", "quit"}:
                print("Stopping approvals.")
                print(
                    f"\nDone. archived={archived} trashed={trashed} "
                    f"skipped={skipped} remaining={len(candidates) - index + 1}"
                )
                return
            print("Please choose a, t, s, or q.")

    print(f"\nDone. archived={archived} trashed={trashed} skipped={skipped}")

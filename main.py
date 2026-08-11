"""Lesson 1 entrypoint: read and print the latest Gmail messages (read-only)."""

from __future__ import annotations

from app.config import MAX_EMAILS_PER_RUN
from app.gmail import (
    GmailAuthError,
    get_message,
    get_service,
    list_messages,
    summarize_message,
)


def fetch_recent_summaries(max_results: int = MAX_EMAILS_PER_RUN) -> list[dict[str, str]]:
    """Authenticate, fetch recent messages, and return display summaries."""
    service = get_service()
    stubs = list_messages(service, max_results=max_results)

    summaries: list[dict[str, str]] = []
    for stub in stubs:
        message = get_message(service, stub["id"])
        summaries.append(summarize_message(message))
    return summaries


def print_summaries(summaries: list[dict[str, str]]) -> None:
    """Print summaries in the Lesson 1 acceptance format."""
    print(f"Found {len(summaries)} emails\n")

    for index, item in enumerate(summaries, start=1):
        print(f"{index}.")
        print(f"From: {item['from']}")
        print(f"Subject: {item['subject']}")
        print(f"Date: {item['date']}")
        print(f"Snippet: {item['snippet']}")
        print()


def main() -> None:
    try:
        summaries = fetch_recent_summaries()
    except GmailAuthError as exc:
        print(f"Authentication error: {exc}")
        raise SystemExit(1) from exc

    print_summaries(summaries)


if __name__ == "__main__":
    main()

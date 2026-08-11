"""Unit tests for Gmail MIME → EmailMessage parsing."""

from __future__ import annotations

import base64

from app.parser import html_to_text, parse


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def test_parse_plain_text_message() -> None:
    message = {
        "id": "msg-1",
        "threadId": "thread-1",
        "snippet": "Interview details",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "recruiter@example.com"},
                {"name": "To", "value": "me@gmail.com"},
                {"name": "Subject", "value": "Your interview is scheduled"},
                {"name": "Date", "value": "Tue, 11 Aug 2026 10:00:00 +0000"},
            ],
            "body": {"data": _b64url("Your interview is scheduled for Monday.")},
        },
    }

    parsed = parse(message)

    assert parsed.message_id == "msg-1"
    assert parsed.thread_id == "thread-1"
    assert parsed.sender == "recruiter@example.com"
    assert parsed.recipient == "me@gmail.com"
    assert parsed.subject == "Your interview is scheduled"
    assert parsed.date == "Tue, 11 Aug 2026 10:00:00 +0000"
    assert parsed.body == "Your interview is scheduled for Monday."
    assert parsed.snippet == "Interview details"


def test_parse_html_only_converts_to_text() -> None:
    html = "<html><body><p>Hello <b>world</b></p><script>alert(1)</script></body></html>"
    message = {
        "id": "msg-2",
        "threadId": "thread-2",
        "snippet": "Hello world",
        "payload": {
            "mimeType": "text/html",
            "headers": [
                {"name": "From", "value": "news@example.com"},
                {"name": "Subject", "value": "Hello"},
            ],
            "body": {"data": _b64url(html)},
        },
    }

    parsed = parse(message)

    assert "Hello" in parsed.body
    assert "world" in parsed.body
    assert "alert" not in parsed.body


def test_parse_multipart_prefers_plain_text() -> None:
    message = {
        "id": "msg-3",
        "threadId": "thread-3",
        "snippet": "Plain wins",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "alerts@example.com"},
                {"name": "Subject", "value": "Status"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64url("Plain body content")},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": _b64url("<p>HTML body content</p>")},
                },
            ],
        },
    }

    parsed = parse(message)
    assert parsed.body == "Plain body content"


def test_parse_missing_fields_does_not_crash() -> None:
    message = {
        "id": "msg-4",
        "threadId": "thread-4",
        "payload": {"mimeType": "text/plain", "headers": [], "body": {}},
    }

    parsed = parse(message)

    assert parsed.message_id == "msg-4"
    assert parsed.subject == ""
    assert parsed.sender == ""
    assert parsed.recipient == ""
    assert parsed.body == ""
    assert parsed.snippet == ""


def test_parse_encoded_subject_header() -> None:
    message = {
        "id": "msg-5",
        "threadId": "thread-5",
        "snippet": "",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {
                    "name": "Subject",
                    "value": "=?UTF-8?B?SGVsbG8g8J+RjQ==?=",  # Hello 👋
                }
            ],
            "body": {"data": _b64url("hi")},
        },
    }

    parsed = parse(message)
    assert "Hello" in parsed.subject


def test_html_to_text_basic() -> None:
    assert "Alpha" in html_to_text("<div>Alpha<br>Beta</div>")
    assert "Beta" in html_to_text("<div>Alpha<br>Beta</div>")

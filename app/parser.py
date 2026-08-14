"""Parse Gmail API MIME messages into EmailMessage models.

Gmail returns nested MIME (plain, HTML, multipart). This layer prefers
text/plain, converts HTML when needed, and never crashes on missing fields.
"""

from __future__ import annotations

import base64
import re
from email.header import decode_header, make_header
from html.parser import HTMLParser
from typing import Any

from app.models import EmailMessage


class _HTMLToText(HTMLParser):
    """Convert HTML into readable plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._chunks.append(data)

    def get_text(self) -> str:
        text = "".join(self._chunks)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


def decode_header_value(value: str | None) -> str:
    """Decode RFC 2047 encoded headers into a Unicode string."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def get_header(message: dict[str, Any], name: str) -> str:
    """Return a decoded header value from a Gmail message (case-insensitive)."""
    headers = message.get("payload", {}).get("headers", [])
    target = name.lower()
    for header in headers:
        if header.get("name", "").lower() == target:
            return decode_header_value(header.get("value"))
    return ""


def _decode_body_data(data: str | None) -> str:
    """Decode Gmail's URL-safe base64 body payload into UTF-8 text."""
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(data + padding)
    return raw.decode("utf-8", errors="replace")


def html_to_text(html: str) -> str:
    """Convert HTML body content into readable plain text."""
    parser = _HTMLToText()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def _walk_parts(part: dict[str, Any]) -> tuple[str | None, str | None]:
    """Recursively collect the first text/plain and text/html bodies."""
    mime_type = (part.get("mimeType") or "").lower()
    plain: str | None = None
    html: str | None = None

    body_data = part.get("body", {}).get("data")
    if mime_type == "text/plain" and body_data:
        plain = _decode_body_data(body_data)
    elif mime_type == "text/html" and body_data:
        html = _decode_body_data(body_data)

    for child in part.get("parts") or []:
        child_plain, child_html = _walk_parts(child)
        if plain is None and child_plain is not None:
            plain = child_plain
        if html is None and child_html is not None:
            html = child_html

    return plain, html


def extract_body(payload: dict[str, Any]) -> str:
    """Prefer text/plain; fall back to HTML converted to text."""
    plain, html = _walk_parts(payload)
    if plain and plain.strip():
        return plain.strip()
    if html and html.strip():
        return html_to_text(html)
    return ""


def parse(message: dict[str, Any]) -> EmailMessage:
    """Convert a raw Gmail API message dict into EmailMessage."""
    payload = message.get("payload") or {}

    return EmailMessage(
        message_id=message.get("id") or "",
        thread_id=message.get("threadId") or "",
        sender=get_header(message, "From"),
        recipient=get_header(message, "To"),
        subject=get_header(message, "Subject"),
        date=get_header(message, "Date"),
        body=extract_body(payload),
        snippet=message.get("snippet") or "",
    )

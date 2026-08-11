# Lesson 2 — Email Parser

## Objective

Normalize Gmail MIME messages into a Pydantic model.

## Create

```text
app/parser.py
```

## Extract

```text
message_id
thread_id
sender
recipient
subject
date
body
snippet
```

## Example model

```python
EmailMessage(
    message_id="...",
    thread_id="...",
    sender="example@example.com",
    recipient="me@gmail.com",
    subject="Your interview is scheduled",
    date="...",
    body="Your interview is scheduled for...",
    snippet="Your interview is scheduled..."
)
```

## Parser requirements

Handle:

- `text/plain`
- `text/html`
- multipart messages
- missing subject
- missing body
- encoded headers
- UTF-8 content

Prefer plain text when available.

If only HTML exists, convert it to readable text.

## Tests

Add unit tests using mocked Gmail messages.

Do not modify the Gmail API client behavior beyond what Lesson 1 already provides.

## Acceptance criteria

- Valid plain-text messages parse cleanly
- HTML-only messages become readable text
- Multipart messages prefer `text/plain`
- Missing fields do not crash the parser

## Next

→ [Lesson 3 — AI Classification](./03-ai-classification.md)

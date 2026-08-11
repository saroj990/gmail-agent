# Lesson 8 — Tool-Based Agent

## Objective

Expose Gmail capabilities as explicit tools with a hard allowlist.

## Tools

```text
get_recent_emails()
read_email()
apply_label()
archive_email()
```

The agent should be able to reason about which tool/action is appropriate.

## Allowlist

```python
ALLOWED_ACTIONS = {
    "LEAVE_IN_INBOX",
    "LABEL_AND_ARCHIVE",
    "NO_ACTION",
}
```

The model must never be able to invent arbitrary Gmail operations.

## Acceptance criteria

- Tools are callable through a controlled interface
- Unknown/disallowed actions are rejected in code
- No path exists for DELETE / send / reply / spam from model output

## Next

→ [Lesson 9 — Human-in-the-Loop](./09-human-in-the-loop.md)

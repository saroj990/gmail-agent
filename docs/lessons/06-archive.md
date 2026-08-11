# Lesson 6 — Archive

## Objective

Archive messages by removing the Gmail INBOX label.

## Implement

```python
archive_message(message_id)
```

In Gmail, archiving can be implemented by removing the Inbox label from the message/thread.

## Safety requirement

Only execute archive when **all** of these are true:

```text
category == TO_PROCESS
AND
confidence >= configured threshold
AND
dry_run == false
```

Example config:

```env
CONFIDENCE_THRESHOLD=0.95
```

## Acceptance criteria

- Archive works on one intentional test email
- Dry-run never archives
- Low-confidence TO_PROCESS does not archive
- IMPORTANT / UNKNOWN never archive

## Next

→ [Lesson 7 — Agent Layer](./07-agent-layer.md)

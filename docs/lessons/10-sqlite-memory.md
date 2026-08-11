# Lesson 10 — SQLite Memory

## Objective

Persist classifications/actions and prevent reprocessing the same message.

## Example table

```sql
CREATE TABLE email_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE,
    thread_id TEXT,
    sender TEXT,
    subject TEXT,
    category TEXT,
    importance TEXT,
    confidence REAL,
    reason TEXT,
    action TEXT,
    created_at TEXT
);
```

## Behavior

- Skip message IDs already present in the table
- Log every classification and executed/proposed action
- Keep the audit trail local (SQLite file should be gitignored)

## Acceptance criteria

- Re-running the agent does not reprocess the same Gmail message IDs
- Audit rows exist for each decision
- Unique constraint on `message_id` is enforced

## After this lesson

MVP memory is done. Continue with:

- [User Preferences](../advanced/user-preferences.md)
- [Confidence Automation](../advanced/confidence-automation.md)
- [Scheduler](../advanced/scheduler.md)
- [MVP Checklist](../mvp-checklist.md)

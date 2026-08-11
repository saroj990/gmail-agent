# Lesson 9 — Human-in-the-Loop

## Objective

Add approval mode before any automatic Gmail mutations.

## Example UX

```text
Email:
LinkedIn — Someone viewed your profile

AI Decision:
TO_PROCESS
Confidence: 0.99

Proposed action:
Apply "To Process" and archive

Approve? [y/N]
```

Only execute after approval.

## Configuration

```env
MODE=dry_run
# MODE=approval
# MODE=automatic
```

Default: `dry_run`

## Mode behavior

| Mode | Behavior |
|------|----------|
| `dry_run` | Report only |
| `approval` | Propose + require explicit confirmation |
| `automatic` | Execute allowlisted actions when guards pass |

## Acceptance criteria

- Default mode is dry-run
- Approval mode blocks until user confirms
- Declined proposals leave Gmail unchanged
- Automatic mode still respects confidence threshold + allowlist

## Next

→ [Lesson 10 — SQLite Memory](./10-sqlite-memory.md)

# Lesson 3 — AI Classification

## Objective

Classify parsed emails with a local Ollama model and return validated structured JSON.

## Architecture

```text
Python
   │
   ▼
Ollama HTTP API
   │
   ▼
Qwen
```

## Output example

```json
{
  "category": "TO_PROCESS",
  "importance": "LOW",
  "confidence": 0.97,
  "reason": "This is a promotional LinkedIn notification.",
  "action": "LABEL_AND_ARCHIVE"
}
```

## Classification schema

Categories (only these three):

```text
IMPORTANT
TO_PROCESS
UNKNOWN
```

Importance:

```text
HIGH
MEDIUM
LOW
```

Allowed actions:

```text
LEAVE_IN_INBOX
LABEL_AND_ARCHIVE
NO_ACTION
```

Do **not** allow in the first implementation:

```text
DELETE
MOVE_TO_SPAM
```

## System prompt (strict)

```text
You are an email classification assistant.

Your job is to classify emails based on whether the user is likely to
need attention from them.

IMPORTANT means:
- Personal messages
- Work messages requiring action
- Interview invitations
- Financial/security alerts
- Important account notifications
- Messages containing deadlines
- Messages requiring a response

TO_PROCESS means:
- Marketing
- Newsletters
- Promotional emails
- Social notifications
- Job recommendation emails
- Routine notifications
- Low-value updates

UNKNOWN means:
- You cannot confidently determine the appropriate category.

Safety rules:
- Never classify an email as IMPORTANT solely because the sender is well-known.
- Look at the actual subject and body.
- If uncertain, use UNKNOWN.
- Never recommend deleting an email.

Return ONLY valid JSON matching the required schema.
```

## Implementation notes

- Validate model output with Pydantic
- Reject/repair invalid JSON safely (prefer fail → UNKNOWN/NO_ACTION)
- Keep classifier independent from Gmail write APIs

## Acceptance criteria

- Valid emails produce schema-valid decisions
- Invalid model output is rejected by tests
- Classifier never returns DELETE or MOVE_TO_SPAM

## Next

→ [Lesson 4 — Dry Run](./04-dry-run.md)

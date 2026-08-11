# Lesson 4 — Dry Run

## Objective

Wire fetch → parse → classify → display with **zero Gmail modifications**.

This is an important milestone. Do not proceed to labels/archive until dry-run looks trustworthy.

## Behavior

1. Fetch emails
2. Parse them
3. Send them to the LLM
4. Display the classification
5. Make **zero Gmail modifications**

## Example output

```text
Analyzing 20 emails...

[1]
From: LinkedIn
Subject: 15 people viewed your profile

Category: TO_PROCESS
Importance: LOW
Confidence: 0.99
Action: LABEL_AND_ARCHIVE
Reason: Routine social notification

[2]
From: recruiter@example.com
Subject: Interview invitation

Category: IMPORTANT
Importance: HIGH
Confidence: 0.98
Action: LEAVE_IN_INBOX
Reason: Interview invitation requiring attention
```

## Configuration

```env
MODE=dry_run
MAX_EMAILS_PER_RUN=20
```

## Acceptance criteria

- Pipeline runs end-to-end on real Gmail data
- Classifications print clearly
- Inbox is unchanged after the run
- `MODE=dry_run` is the default

## Next

→ [Lesson 5 — Gmail Labels](./05-gmail-labels.md)

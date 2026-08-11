# Suggested Cursor Prompts

Ask Cursor to implement **one lesson at a time**.

## Prompt 1 — Lesson 1

```text
Read docs/overview.md and docs/lessons/01-gmail-api.md.

Implement Lesson 1 only.

Create a Python Gmail API client using OAuth 2.0 with the
gmail.readonly scope.

The application should authenticate and print the latest 10 Gmail
messages with sender, subject, date and snippet.

Do not modify any Gmail data.

Create clean modules and tests.

Do not implement the AI classifier yet.
```

## Prompt 2 — Lesson 2

```text
Read docs/lessons/02-email-parser.md.

Implement Lesson 2.

Create an email parser that converts Gmail API MIME messages into a
normalized Pydantic EmailMessage model.

Support text/plain, text/html and multipart messages.

Add unit tests using mocked Gmail messages.

Do not modify the Gmail API client behavior.
```

## Prompt 3 — Lesson 3

```text
Read docs/lessons/03-ai-classification.md.

Implement Lesson 3.

Create a local Ollama classifier.

Use structured Pydantic output with:
category, importance, confidence, reason and action.

Allowed categories:
IMPORTANT, TO_PROCESS, UNKNOWN.

Allowed actions:
LEAVE_IN_INBOX, LABEL_AND_ARCHIVE, NO_ACTION.

The classifier must never return DELETE or MOVE_TO_SPAM.

Add tests for parsing and validating model output.
```

## Prompt 4 — Lesson 4

```text
Read docs/lessons/04-dry-run.md.

Implement Lesson 4 dry-run mode.

Fetch emails, parse them, classify them with Ollama and print the
classification.

Do not modify Gmail in any way.

Add configuration for MAX_EMAILS_PER_RUN and MODE=dry_run.
```

## Prompt 5 — Lesson 5

```text
Read docs/lessons/05-gmail-labels.md.

Implement Lesson 5.

Add Gmail label management and create/get the "To Process" label.

Add tests.

Do not archive or delete emails yet.
```

## Prompt 6 — Lesson 6

```text
Read docs/lessons/06-archive.md.

Implement Lesson 6.

Add archive functionality by removing the Gmail INBOX label.

Only allow the action when:
category == TO_PROCESS
confidence >= CLASSIFICATION_THRESHOLD
MODE != dry_run

Add safety checks and tests.
```

## Prompt 7 — Lesson 7

```text
Read docs/lessons/07-agent-layer.md.

Implement Lesson 7 and create the agent orchestration layer.

Keep Gmail API operations, parsing, classification, decisions and
actions in separate modules.

The agent must use an explicit action allowlist.

Do not introduce LangChain or LangGraph.
```

## Prompt 8 — Lesson 9

```text
Read docs/lessons/09-human-in-the-loop.md.

Implement Lesson 9 human approval mode.

Support:
MODE=dry_run
MODE=approval
MODE=automatic

Default to dry_run.

In approval mode, display the proposed Gmail action and require
explicit user confirmation before executing it.
```

## Prompt 9 — Lesson 10

```text
Read docs/lessons/10-sqlite-memory.md.

Implement SQLite decision memory.

Prevent already processed Gmail message IDs from being processed
again.

Add an audit trail for every classification and action.
```

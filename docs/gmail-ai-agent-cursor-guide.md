# Gmail AI Inbox Agent — Cursor Build Guide

## Goal

Build a local-first AI agent that reads Gmail messages, classifies them, and eventually labels/archives unimportant emails.

### Initial safety goal

The first version must be **read-only**.

Do not modify, archive, delete, or label any email until the classification pipeline has been tested in dry-run mode.

---

# 1. Target Architecture

```text
                         Gmail
                           │
                           ▼
                      Gmail API
                           │
                           ▼
                  ┌─────────────────┐
                  │  Gmail Agent    │
                  └────────┬────────┘
                           │
                    Email Parser
                           │
                           ▼
                     Ollama / Qwen
                           │
                           ▼
                  Structured Decision
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         IMPORTANT     TO_PROCESS      UNKNOWN
             │             │             │
             ▼             ▼             ▼
       Leave Inbox    Label + Archive  Ask User
```

---

# 2. MVP Behavior

The agent should eventually do this:

```text
New Gmail email
       ↓
Read sender + subject + body
       ↓
Send relevant content to local LLM
       ↓
Classify email
       ↓
IMPORTANT
    → leave in Inbox

TO_PROCESS
    → apply "To Process" label
    → archive

UNKNOWN
    → do nothing
```

### Important safety rule

Initially:

```text
AI classification → report only
```

Later:

```text
AI classification → proposed action → human approval
```

Only after the system is reliable should selected actions become automatic.

**Never allow the LLM to directly delete emails.**

---

# 3. Technology Stack

Use:

- Python 3.11+
- Gmail API
- Google OAuth 2.0
- Ollama
- Qwen model
- SQLite
- Pydantic
- pytest
- python-dotenv

Do not introduce LangChain or LangGraph initially.

Build the core system directly so the underlying agent architecture is understood first.

Later, LangGraph can be introduced if stateful workflows become useful.

---

# 4. Project Structure

Create:

```text
gmail-ai-agent/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── gmail.py
│   ├── parser.py
│   ├── classifier.py
│   ├── models.py
│   ├── agent.py
│   ├── database.py
│   └── actions.py
│
├── tests/
│   ├── test_parser.py
│   ├── test_classifier.py
│   └── test_agent.py
│
├── credentials.json
├── token.json
├── .env
├── .gitignore
├── requirements.txt
├── main.py
└── README.md
```

Never commit:

```text
credentials.json
token.json
.env
```

---

# 5. Lesson 1 — Gmail API

## Objective

Connect Python to Gmail using OAuth and read emails.

### Steps

1. Create a Google Cloud project.
2. Enable Gmail API.
3. Configure OAuth consent screen.
4. Create an OAuth Desktop Application credential.
5. Download the OAuth client credentials.
6. Save them as:

```text
credentials.json
```

7. Run the Python application.
8. Complete Google's OAuth flow.
9. Store the resulting token locally in:

```text
token.json
```

### Gmail permission

Start with the minimum useful read-only scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Do not request modify/delete permissions in Lesson 1.

---

# 6. Lesson 1 Implementation

Install:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Create a Gmail client that can:

```python
get_service()
list_messages()
get_message()
```

The first test should simply print:

```text
From:
Subject:
Date:
Snippet:
```

for the latest 10 emails.

### Acceptance criteria

Running:

```bash
python main.py
```

should produce something similar to:

```text
Found 10 emails

1.
From: LinkedIn <notifications@linkedin.com>
Subject: Someone viewed your profile
Date: ...

2.
From: Naukri <...>
Subject: Jobs matching your profile
Date: ...
```

No Gmail data should be modified.

---

# 7. Lesson 2 — Email Parser

Gmail messages are returned as MIME structures.

Create:

```text
app/parser.py
```

Extract:

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

Normalize the email into a Python/Pydantic model.

Example:

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

### Parser requirements

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

---

# 8. Lesson 3 — AI Classification

Use Ollama locally.

Example architecture:

```text
Python
   │
   ▼
Ollama HTTP API
   │
   ▼
Qwen
```

The classifier should return structured JSON.

Example:

```json
{
  "category": "TO_PROCESS",
  "importance": "LOW",
  "confidence": 0.97,
  "reason": "This is a promotional LinkedIn notification.",
  "action": "LABEL_AND_ARCHIVE"
}
```

---

# 9. Classification Schema

Start with only three categories:

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

Do not allow:

```text
DELETE
MOVE_TO_SPAM
```

in the first implementation.

---

# 10. Classification Prompt

Use a strict system prompt similar to:

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

---

# 11. Lesson 4 — Dry Run

This is an important milestone.

The program should:

1. Fetch emails.
2. Parse them.
3. Send them to the LLM.
4. Display the classification.
5. Make **zero Gmail modifications**.

Example:

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
Confidence: 0.97
Action: LEAVE_IN_INBOX
Reason: Requires user attention
```

---

# 12. Lesson 5 — Gmail Labels

Only after dry-run classification works reliably.

Create a Gmail label:

```text
To Process
```

Implement:

```python
create_label(name)
get_label_id(name)
apply_label(message_id, label_id)
```

Test labeling manually on a single test email.

---

# 13. Lesson 6 — Archive

Implement:

```python
archive_message(message_id)
```

In Gmail, archiving can be implemented by removing the Inbox label from the message/thread.

### Safety requirement

Only execute archive when:

```text
category == TO_PROCESS
AND
confidence >= configured threshold
AND
dry_run == false
```

Example:

```text
CONFIDENCE_THRESHOLD=0.95
```

---

# 14. Lesson 7 — Agent Layer

Create:

```text
app/agent.py
```

The agent should orchestrate:

```text
Fetch
  ↓
Parse
  ↓
Classify
  ↓
Validate
  ↓
Decide
  ↓
Execute
```

Conceptually:

```python
emails = gmail.get_messages()

for email in emails:
    parsed = parser.parse(email)
    decision = classifier.classify(parsed)
    action = agent.decide(decision)

    if action == "LABEL_AND_ARCHIVE":
        actions.label_and_archive(email)
```

Keep the Gmail API operations separate from the agent logic.

---

# 15. Lesson 8 — Tool-Based Agent

Turn Gmail capabilities into explicit tools:

```text
get_recent_emails()
read_email()
apply_label()
archive_email()
```

The agent should be able to reason about which tool/action is appropriate.

However, keep an allowlist:

```python
ALLOWED_ACTIONS = {
    "LEAVE_IN_INBOX",
    "LABEL_AND_ARCHIVE",
    "NO_ACTION",
}
```

The model must never be able to invent arbitrary Gmail operations.

---

# 16. Lesson 9 — Human-in-the-Loop

Before automatic actions, add approval mode.

Example:

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

Add configuration:

```text
MODE=dry_run
MODE=approval
MODE=automatic
```

Default:

```text
MODE=dry_run
```

---

# 17. Lesson 10 — SQLite Memory

Use SQLite to record decisions.

Example table:

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

This prevents processing the same email repeatedly.

---

# 18. User Preferences

Later, allow rules/preferences such as:

```text
Always keep GitHub pull request emails.

LinkedIn profile-view notifications are low priority.

Keep emails from my manager important.

Job interview invitations are always important.

Marketing newsletters should go to To Process.
```

Store these preferences separately.

Example:

```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference TEXT NOT NULL,
    created_at TEXT
);
```

The classifier can receive relevant preferences as context.

---

# 19. Confidence-Based Automation

Eventually:

```text
confidence >= 0.95
    AND
category == TO_PROCESS
    ↓
automatic label + archive
```

But:

```text
confidence < 0.95
    ↓
NO_ACTION
```

This creates a conservative system.

---

# 20. Scheduler

Once everything is stable, run periodically.

Initially use cron:

```bash
*/15 * * * * /path/to/venv/bin/python /path/to/gmail-ai-agent/main.py
```

Do not process every email repeatedly.

Use the database and Gmail message IDs to track processed messages.

---

# 21. Configuration

Use `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

CLASSIFICATION_THRESHOLD=0.95

MODE=dry_run

GMAIL_LABEL=To Process

MAX_EMAILS_PER_RUN=20
```

Never put secrets directly in Python source.

---

# 22. Testing Strategy

Test each layer independently.

### Gmail

```text
Can authenticate?
Can list messages?
Can read message?
```

### Parser

```text
Can parse plain text?
Can parse HTML?
Can parse multipart?
```

### Classifier

```text
Does valid email return valid JSON?
Does invalid model output get rejected?
```

### Agent

```text
IMPORTANT → no modification
TO_PROCESS → correct action
UNKNOWN → no action
```

### Gmail Actions

Test against one test email before batch processing.

---

# 23. Guardrails

These are mandatory.

### Never:

- Delete emails automatically.
- Send emails automatically.
- Reply automatically.
- Forward emails automatically.
- Change account settings.
- Mark important based only on sender.
- Execute arbitrary model-generated API calls.

### Always:

- Validate LLM output.
- Use an action allowlist.
- Keep dry-run mode.
- Keep an audit log.
- Set a maximum number of emails per run.
- Require approval before enabling automatic actions.

---

# 24. Future Architecture

Once the MVP works:

```text
                       Gmail
                         │
                         ▼
                    Gmail API
                         │
                         ▼
                ┌─────────────────┐
                │   AI Agent      │
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Gmail Tool     Classifier     Memory
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   Decision Engine
                         │
                 ┌───────┴────────┐
                 ▼                ▼
             Automatic        Human Review
                 │                │
                 └───────┬────────┘
                         ▼
                      Gmail
```

Possible future technologies:

```text
LangGraph
FastAPI
React
PostgreSQL
Redis
MCP
```

Do not add these until the basic Python implementation works.

---

# 25. Suggested Cursor Development Order

Ask Cursor to implement one lesson at a time.

## Prompt 1

```text
Read the project README.

Implement Lesson 1 only.

Create a Python Gmail API client using OAuth 2.0 with the
gmail.readonly scope.

The application should authenticate and print the latest 10 Gmail
messages with sender, subject, date and snippet.

Do not modify any Gmail data.

Create clean modules and tests.

Do not implement the AI classifier yet.
```

## Prompt 2

```text
Implement Lesson 2.

Create an email parser that converts Gmail API MIME messages into a
normalized Pydantic EmailMessage model.

Support text/plain, text/html and multipart messages.

Add unit tests using mocked Gmail messages.

Do not modify the Gmail API client behavior.
```

## Prompt 3

```text
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

## Prompt 4

```text
Implement Lesson 4 dry-run mode.

Fetch emails, parse them, classify them with Ollama and print the
classification.

Do not modify Gmail in any way.

Add configuration for MAX_EMAILS_PER_RUN and MODE=dry_run.
```

## Prompt 5

```text
Implement Lesson 5.

Add Gmail label management and create/get the "To Process" label.

Add tests.

Do not archive or delete emails yet.
```

## Prompt 6

```text
Implement Lesson 6.

Add archive functionality by removing the Gmail INBOX label.

Only allow the action when:
category == TO_PROCESS
confidence >= CLASSIFICATION_THRESHOLD
MODE != dry_run

Add safety checks and tests.
```

## Prompt 7

```text
Implement Lesson 7 and create the agent orchestration layer.

Keep Gmail API operations, parsing, classification, decisions and
actions in separate modules.

The agent must use an explicit action allowlist.

Do not introduce LangChain or LangGraph.
```

## Prompt 8

```text
Implement Lesson 9 human approval mode.

Support:
MODE=dry_run
MODE=approval
MODE=automatic

Default to dry_run.

In approval mode, display the proposed Gmail action and require
explicit user confirmation before executing it.
```

## Prompt 9

```text
Implement SQLite decision memory.

Prevent already processed Gmail message IDs from being processed
again.

Add an audit trail for every classification and action.
```

---

# 26. Definition of Done — MVP

The MVP is complete when:

- [ ] Gmail OAuth works
- [ ] Latest emails can be read
- [ ] MIME emails are parsed
- [ ] Ollama classification works
- [ ] Classification output is validated
- [ ] Dry-run mode works
- [ ] "To Process" label can be created
- [ ] One test email can be labeled
- [ ] One test email can be archived
- [ ] Agent orchestration works
- [ ] Human approval mode works
- [ ] SQLite audit log works
- [ ] Duplicate processing is prevented
- [ ] No automatic deletion exists
- [ ] Default mode is dry-run

---

# 27. Final Goal

The finished system should eventually behave like:

```text
Every 15 minutes
       ↓
Check new Gmail messages
       ↓
AI reads them
       ↓
Understands importance
       ↓
             ┌──────────────────────┐
             │                      │
        Important              Low value
             │                      │
             ▼                      ▼
          Inbox              "To Process"
                                    │
                                    ▼
                                  Archive
```

The key principle is:

> **AI decides; deterministic code controls what the AI is allowed to do.**

This separation makes the system safer, easier to test, and much easier to extend into a real AI agent later.

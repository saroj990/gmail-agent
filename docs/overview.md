# Overview

## Goal

Build a local-first AI agent that reads Gmail messages, classifies them, and eventually labels/archives unimportant emails.

### Initial safety goal

The first version must be **read-only**.

Do not modify, archive, delete, or label any email until the classification pipeline has been tested in dry-run mode.

---

## Target architecture

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

## MVP behavior

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

### Safety progression

```text
1. AI classification → report only          (dry_run)
2. AI classification → proposed action      (approval)
3. Selected actions become automatic        (automatic, high confidence)
```

**Never allow the LLM to directly delete emails.**

---

## Technology stack

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

---

## Project structure

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
├── credentials.json   # local only
├── token.json         # local only
├── .env               # local only
├── .gitignore
├── requirements.txt
├── main.py
└── README.md
```

Never commit: `credentials.json`, `token.json`, `.env`, or this `docs/` folder.

---

## Final goal

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

> **AI decides; deterministic code controls what the AI is allowed to do.**

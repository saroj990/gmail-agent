# Implementation Plan

## Product goal

Build a local-first Gmail AI inbox agent that:

1. Reads Gmail messages via OAuth
2. Parses MIME into a clean model
3. Classifies with local Ollama + Qwen
4. Eventually labels/archives low-value mail
5. Keeps important mail in Inbox

**Safety principle:** AI decides; deterministic code controls what the AI is allowed to do.

Default mode is always `dry_run`. Never allow LLM-driven delete/send/reply.

---

## Phases

```text
Phase A — Read & Classify (Lessons 1–4)
Phase B — Safe Actions (Lessons 5–6)
Phase C — Agent Control (Lessons 7–9)
Phase D — Memory & Ops (Lesson 10 + advanced)
Phase E — Automation (preferences, scheduler, confidence)
```

---

## Phase A — Read & Classify

| Step | Lesson | Deliverable | Exit criteria |
|------|--------|-------------|---------------|
| A1 | 1 | Gmail OAuth client, `gmail.readonly` | Prints latest 10 emails; no Gmail writes |
| A2 | 2 | `parser.py` + `EmailMessage` model | Plain/HTML/multipart parsed; unit tests pass |
| A3 | 3 | Ollama classifier + Pydantic schema | Valid JSON only; DELETE/SPAM rejected |
| A4 | 4 | End-to-end dry-run CLI | Fetch → parse → classify → print; zero mods |

**Phase A done when:** dry-run on real inbox looks trustworthy for a sample of emails.

---

## Phase B — Safe Actions

| Step | Lesson | Deliverable | Exit criteria |
|------|--------|-------------|---------------|
| B1 | 5 | Create/get/apply "To Process" label | Works on one test email |
| B2 | 6 | Archive by removing INBOX | Only when TO_PROCESS + high confidence + not dry-run |

**Phase B done when:** one intentional test email can be labeled and archived under guards.

---

## Phase C — Agent Control

| Step | Lesson | Deliverable | Exit criteria |
|------|--------|-------------|---------------|
| C1 | 7 | `agent.py` orchestration | Fetch → parse → classify → validate → decide → execute |
| C2 | 8 | Explicit tool allowlist | Model cannot invent Gmail operations |
| C3 | 9 | Modes: dry_run / approval / automatic | Default dry_run; approval requires `y` |

**Phase C done when:** approval mode is usable daily without accidental archives.

---

## Phase D — Memory & Ops

| Step | Lesson / doc | Deliverable | Exit criteria |
|------|--------------|-------------|---------------|
| D1 | 10 | SQLite decisions table | No duplicate processing; audit trail |
| D2 | configuration | `.env` + `config.py` | Threshold, mode, max emails configurable |
| D3 | testing | Layered pytest suite | Parser/classifier/agent tests green |
| D4 | guardrails | Hard checks in code | Never delete/send; allowlist enforced |

**Phase D done when:** MVP checklist is complete (see `mvp-checklist.md`).

---

## Phase E — Post-MVP Automation

| Step | Topic | Notes |
|------|-------|-------|
| E1 | User preferences | Inject rules into classifier context |
| E2 | Confidence automation | Auto only if confidence ≥ threshold |
| E3 | Scheduler | Cron every 15 minutes; skip processed IDs |
| E4 | Future stack | LangGraph / FastAPI / UI only after Python core is solid |

---

## Suggested project layout (code — tracked)

```text
gmail-ai-agent/
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
├── tests/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```

Docs stay under `docs/` (gitignored). Secrets stay local (`credentials.json`, `token.json`, `.env`).

---

## Tech stack (MVP)

- Python 3.11+
- Gmail API + Google OAuth 2.0
- Ollama + Qwen
- SQLite
- Pydantic
- pytest
- python-dotenv

Do **not** add LangChain/LangGraph until Phase E.

---

## Modes (runtime)

| Mode | Behavior |
|------|----------|
| `dry_run` | Classify + report only (default) |
| `approval` | Propose action; wait for human `y/N` |
| `automatic` | Execute allowlisted actions when confidence ≥ threshold |

---

## Classification contract

**Categories:** `IMPORTANT` | `TO_PROCESS` | `UNKNOWN`  
**Importance:** `HIGH` | `MEDIUM` | `LOW`  
**Actions:** `LEAVE_IN_INBOX` | `LABEL_AND_ARCHIVE` | `NO_ACTION`

Forbidden: `DELETE`, `MOVE_TO_SPAM`, send, reply, forward.

---

## Execution order for Cursor

Work **one lesson file at a time**. Use the matching prompt in `cursor-prompts.md`.

Recommended cadence:

1. Implement lesson
2. Run acceptance checks in that lesson file
3. Add/adjust tests
4. Only then open the next lesson

Do not skip Lesson 4 (dry-run) before any write scopes or archive code.

---

## Risk checklist

- [ ] Start with `gmail.readonly` only
- [ ] Request modify scopes only when entering Lesson 5+
- [ ] Cap `MAX_EMAILS_PER_RUN`
- [ ] Validate all LLM JSON with Pydantic
- [ ] Keep action allowlist in code, not in the prompt alone
- [ ] Never commit `credentials.json`, `token.json`, `.env`, or `docs/`

# Gmail AI Inbox Agent

Local-first Gmail inbox agent. Default mode is **dry-run** (classify only).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google Cloud / Gmail API

1. Enable **Gmail API** and create **OAuth Desktop** credentials.
2. Save as `credentials.json` in the project root.
3. Add yourself as an OAuth test user.

Uses `gmail.modify` (labels/archive; no permanent delete). If upgrading from readonly:

```bash
rm token.json
python main.py ensure-label
```

### Ollama / config

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
MODE=dry_run
GMAIL_LABEL=To Process
CONFIDENCE_THRESHOLD=0.95
```

### Run (dry-run classify)

```bash
python main.py
```

### Labels + archive (manual one-email test)

```bash
# 1) Dry-run and copy a Message-ID
python main.py

# 2) Ensure label exists
python main.py ensure-label

# 3a) Label only
MODE=automatic python main.py apply-label MESSAGE_ID

# 3b) Label + archive (removes INBOX)
MODE=automatic python main.py label-and-archive MESSAGE_ID

# 3c) Archive only
MODE=automatic python main.py archive MESSAGE_ID
```

Pipeline auto label+archive only when:
`MODE != dry_run` AND category `TO_PROCESS` AND confidence ≥ threshold.

### Tests

```bash
pytest
```

## Lessons so far

| Lesson | Status |
|--------|--------|
| 1 Gmail API (readonly OAuth) | Done |
| 2 Email parser (Pydantic) | Done |
| 3 AI classification (Ollama) | Done |
| 4 Dry-run mode | Done |
| 5 Gmail labels | Done |
| 6 Archive | Done |

## Safety

- Default `MODE=dry_run` never writes
- Writes require `approval` or `automatic`
- Archive requires TO_PROCESS + confidence ≥ threshold
- Never permanent delete
- Never commit `credentials.json`, `token.json`, or `.env`

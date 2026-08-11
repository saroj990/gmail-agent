# Gmail AI Inbox Agent

Local-first Gmail inbox agent. Default mode is **dry-run** (classify only). Lesson 5 adds label helpers.

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

Lesson 5 uses `gmail.modify` (labels; no permanent delete). If you previously authorized readonly only:

```bash
rm token.json
python main.py ensure-label
```

Re-consent in the browser when prompted.

### Ollama

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
MODE=dry_run
GMAIL_LABEL=To Process
```

### Run (dry-run classify)

```bash
python main.py
```

### Lesson 5 — labels

Recommended workflow:

```bash
# 1) Dry-run: classify and print Message-ID values (no Gmail writes)
python main.py

# 2) Ensure the label exists
python main.py ensure-label

# 3) Apply label to one Message-ID you copied from the dry-run output
MODE=automatic python main.py apply-label MESSAGE_ID
```

Does **not** archive yet (Lesson 6).

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

## Safety

- Default `MODE=dry_run` never writes
- Label apply requires `approval` or `automatic`
- No archive/delete in Lesson 5
- Never commit `credentials.json`, `token.json`, or `.env`

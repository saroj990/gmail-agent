# Gmail AI Inbox Agent

Local-first Gmail inbox agent. Currently **read-only**: OAuth + parse recent messages.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google Cloud / Gmail API

1. Create a Google Cloud project and enable **Gmail API**.
2. Configure OAuth consent (add yourself as a test user).
3. Create **OAuth client ID → Desktop app**.
4. Save the downloaded JSON as `credentials.json` in the project root.

### Run

```bash
python main.py
```

First run opens a browser for Google login and saves `token.json`.

### Tests

```bash
pytest
```

## Lessons so far

| Lesson | Status |
|--------|--------|
| 1 Gmail API (readonly OAuth) | Done |
| 2 Email parser (Pydantic) | Done |

## Safety

- Scope: `https://www.googleapis.com/auth/gmail.readonly`
- No labels, archive, delete, or send yet
- Never commit `credentials.json`, `token.json`, or `.env`

## Project layout

```text
app/
  config.py
  gmail.py
  models.py
  parser.py
main.py
tests/
requirements.txt
```

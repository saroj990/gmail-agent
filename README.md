# Gmail AI Inbox Agent

Local-first Gmail inbox agent. Currently **read-only**: OAuth + parse + classify (no Gmail writes).

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

### Ollama (Lesson 3)

```bash
# Install Ollama, then:
ollama pull qwen2.5:7b
```

Optional `.env` (see `.env.example`):

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

### Run

```bash
python main.py
```

Fetches recent emails, parses them, classifies with Ollama, and prints decisions. Inbox is not modified.

### Tests

```bash
pytest
```

## Lessons so far

| Lesson | Status |
|--------|--------|
| 1 Gmail API (readonly OAuth) | Done |
| 2 Email parser (Pydantic) | Done |
| 3 AI classification (Ollama/Qwen) | Done |

## Safety

- Scope: `gmail.readonly`
- Classifier never returns DELETE / MOVE_TO_SPAM
- Invalid model output → UNKNOWN / NO_ACTION
- Never commit `credentials.json`, `token.json`, or `.env`

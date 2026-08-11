# Configuration

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

Ship a tracked `.env.example` without secrets; keep real `.env` gitignored.

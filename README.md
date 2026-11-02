# Gmail AI Inbox Agent

Local-first Gmail inbox agent. Default mode is **dry-run** (classify only).

**Docs:** [docs/README.md](docs/README.md) · [Implementation plan](docs/IMPLEMENTATION_PLAN.md) · [Overview](docs/overview.md)

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

### Classifier / config

Default is local Ollama. Gemini is optional and faster; email text is sent to Google.

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
MODE=dry_run
GMAIL_LABEL=To Process
CONFIDENCE_THRESHOLD=0.95
DATABASE_PATH=data/decisions.db
```

To use Gemini, copy these into your **local** `.env` (not committed):

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
```

Create the key at [Google AI Studio](https://aistudio.google.com/apikey).

### Modes ([Lesson 9](docs/lessons/09-human-in-the-loop.md))

| MODE | Behavior |
|------|----------|
| `dry_run` (default) | Classify/report only |
| `approval` | Ask `Approve? [y/N]` before each label+archive |
| `automatic` | Label+archive when confidence guards pass |

```bash
MODE=approval python main.py
```

Richer interactive options (archive/trash/skip):

```bash
python main.py review
```

### Web UI

A local Svelte UI with Google sign-in, a dashboard for dry runs and real runs,
and a preferences page. Needs Node from [`.nvmrc`](.nvmrc) and pnpm.

```bash
nvm use
cd web && pnpm install && pnpm build && cd ..
python main.py serve          # http://localhost:8000
```

- **Dry run** classifies only and does not record emails as processed. You can
  then tick eligible rows and click **Label + archive selected**.
- **Run for real** labels and archives every `TO_PROCESS` email at or above the
  confidence threshold, same as `MODE=automatic`.
- **Preferences** (provider, Ollama URL and model, Gemini model, label,
  threshold, emails per run) are saved to `data/settings.json` and only apply to
  UI runs. The Gemini API key stays in `.env`. `MODE` in `.env` only affects
  the CLI.

The server binds to `127.0.0.1` only. For frontend development, run
`python main.py serve` and `pnpm dev` (in `web/`) side by side; see
[web/README.md](web/README.md).

### Run via agent ([Lesson 7](docs/lessons/07-agent-layer.md))

```bash
python main.py
```

Orchestration lives in `app/agent.py`:
Fetch → Parse → Classify → Validate → Decide → Execute

Gmail mutations go only through allowlisted tools in `app/tools.py`
([Lesson 8](docs/lessons/08-tool-based-agent.md)):
`get_recent_emails`, `read_email`, `apply_label`, `archive_email`.

### Memory ([Lesson 10](docs/lessons/10-sqlite-memory.md))

Processed `message_id`s are stored in `data/decisions.db` (gitignored).
Re-runs skip emails already in that database.

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

## Lessons

| Lesson | Status | Guide |
|--------|--------|-------|
| 1 Gmail API | Done | [docs/lessons/01-gmail-api.md](docs/lessons/01-gmail-api.md) |
| 2 Email parser | Done | [docs/lessons/02-email-parser.md](docs/lessons/02-email-parser.md) |
| 3 AI classification | Done | [docs/lessons/03-ai-classification.md](docs/lessons/03-ai-classification.md) |
| 4 Dry-run mode | Done | [docs/lessons/04-dry-run.md](docs/lessons/04-dry-run.md) |
| 5 Gmail labels | Done | [docs/lessons/05-gmail-labels.md](docs/lessons/05-gmail-labels.md) |
| 6 Archive | Done | [docs/lessons/06-archive.md](docs/lessons/06-archive.md) |
| 7 Agent layer | Done | [docs/lessons/07-agent-layer.md](docs/lessons/07-agent-layer.md) |
| 8 Tool-based agent | Done | [docs/lessons/08-tool-based-agent.md](docs/lessons/08-tool-based-agent.md) |
| 9 Human-in-the-loop | Done | [docs/lessons/09-human-in-the-loop.md](docs/lessons/09-human-in-the-loop.md) |
| 10 SQLite memory | Done | [docs/lessons/10-sqlite-memory.md](docs/lessons/10-sqlite-memory.md) |

More docs: [docs/](docs/README.md) · [MVP checklist](docs/mvp-checklist.md) · [Guardrails](docs/advanced/guardrails.md) · [Future](docs/advanced/future.md)

## Safety

- Default `MODE=dry_run` never writes
- Writes require `approval` or `automatic`
- Archive requires TO_PROCESS + confidence ≥ threshold
- Never permanent delete
- Never commit `credentials.json`, `token.json`, or `.env`

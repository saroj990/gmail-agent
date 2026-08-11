# Gmail AI Inbox Agent

Local-first Gmail inbox agent. Lesson 1 is **read-only**: authenticate with Google OAuth and print recent messages.

## Lesson 1 — setup

### 1. Python env

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Google Cloud / Gmail API

1. Create a Google Cloud project.
2. Enable **Gmail API**.
3. Configure the **OAuth consent screen** (External is fine for personal use; add your Google account as a test user).
4. Create credentials: **OAuth client ID → Desktop app**.
5. Download the JSON and save it in the project root as:

```text
credentials.json
```

### 3. Run

```bash
python main.py
```

On first run, a browser window opens for Google login. The refresh token is saved as `token.json`.

Expected shape:

```text
Found 10 emails

1.
From: ...
Subject: ...
Date: ...
Snippet: ...
```

### 4. Tests

```bash
pytest
```

## Safety

- Scope used: `https://www.googleapis.com/auth/gmail.readonly`
- No labels, archive, delete, or send in Lesson 1
- Never commit `credentials.json`, `token.json`, or `.env`

## Project layout

```text
app/
  config.py
  gmail.py
main.py
tests/
requirements.txt
```

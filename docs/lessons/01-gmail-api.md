# Lesson 1 — Gmail API

## Objective

Connect Python to Gmail using OAuth and read emails.

## Steps

1. Create a Google Cloud project.
2. Enable Gmail API.
3. Configure OAuth consent screen.
4. Create an OAuth Desktop Application credential.
5. Download the OAuth client credentials.
6. Save them as `credentials.json`.
7. Run the Python application.
8. Complete Google's OAuth flow.
9. Store the resulting token locally in `token.json`.

## Gmail permission

Start with the minimum useful read-only scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Do not request modify/delete permissions in Lesson 1.

## Install

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Implementation

Create a Gmail client that can:

```python
get_service()
list_messages()
get_message()
```

The first test should simply print `From`, `Subject`, `Date`, `Snippet` for the latest 10 emails.

## Acceptance criteria

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

## Next

→ [Lesson 2 — Email Parser](./02-email-parser.md)

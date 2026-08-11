# Scheduler (Post-MVP)

Once everything is stable, run periodically.

Initially use cron:

```bash
*/15 * * * * /path/to/venv/bin/python /path/to/gmail-ai-agent/main.py
```

Do not process every email repeatedly.

Use the database and Gmail message IDs to track processed messages.

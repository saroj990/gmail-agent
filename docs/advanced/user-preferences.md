# User Preferences (Post-MVP)

Allow rules/preferences such as:

```text
Always keep GitHub pull request emails.

LinkedIn profile-view notifications are low priority.

Keep emails from my manager important.

Job interview invitations are always important.

Marketing newsletters should go to To Process.
```

## Storage example

```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference TEXT NOT NULL,
    created_at TEXT
);
```

The classifier can receive relevant preferences as context.

# Confidence-Based Automation (Post-MVP)

Eventually:

```text
confidence >= 0.95
    AND
category == TO_PROCESS
    ↓
automatic label + archive
```

But:

```text
confidence < 0.95
    ↓
NO_ACTION
```

This creates a conservative system. Prefer over-skipping to over-acting.

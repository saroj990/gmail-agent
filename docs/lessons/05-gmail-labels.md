# Lesson 5 — Gmail Labels

## Prerequisite

Only after dry-run classification works reliably (Lesson 4).

## Objective

Create and apply a Gmail label named:

```text
To Process
```

## Implement

```python
create_label(name)
get_label_id(name)
apply_label(message_id, label_id)
```

You will need Gmail modify scopes beyond readonly for this lesson. Request the minimum scope required for labels.

## Safety

- Do not archive or delete emails yet
- Test labeling manually on a **single** test email first
- Keep dry-run capable of skipping writes

## Acceptance criteria

- "To Process" label can be created or fetched if it already exists
- One test email can receive the label
- No archive/delete side effects

## Next

→ [Lesson 6 — Archive](./06-archive.md)

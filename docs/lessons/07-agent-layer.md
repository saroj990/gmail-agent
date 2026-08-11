# Lesson 7 — Agent Layer

## Objective

Orchestrate the full pipeline in `app/agent.py` while keeping modules separate.

## Flow

```text
Fetch
  ↓
Parse
  ↓
Classify
  ↓
Validate
  ↓
Decide
  ↓
Execute
```

## Conceptual shape

```python
emails = gmail.get_messages()

for email in emails:
    parsed = parser.parse(email)
    decision = classifier.classify(parsed)
    action = agent.decide(decision)

    if action == "LABEL_AND_ARCHIVE":
        actions.label_and_archive(email)
```

## Rules

- Keep Gmail API operations separate from agent logic
- Keep parsing, classification, decisions, and actions in separate modules
- Use an explicit action allowlist
- Do not introduce LangChain or LangGraph

## Acceptance criteria

- Agent can run the full pipeline
- IMPORTANT → no modification
- TO_PROCESS → correct proposed/executed action (mode-dependent)
- UNKNOWN → no action

## Next

→ [Lesson 8 — Tool-Based Agent](./08-tool-based-agent.md)

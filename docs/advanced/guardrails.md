# Guardrails

These are mandatory.

## Never

- Delete emails automatically
- Send emails automatically
- Reply automatically
- Forward emails automatically
- Change account settings
- Mark important based only on sender
- Execute arbitrary model-generated API calls

## Always

- Validate LLM output
- Use an action allowlist
- Keep dry-run mode
- Keep an audit log
- Set a maximum number of emails per run
- Require approval before enabling automatic actions

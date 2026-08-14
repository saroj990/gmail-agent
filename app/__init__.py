"""Gmail AI Inbox Agent package.

Layering (keep these separate):
  config     — env settings
  gmail      — OAuth + Gmail API
  parser     — MIME → EmailMessage
  classifier — LLM JSON decision (Ollama or Gemini)
  actions    — when a write is allowed
  tools      — allowlisted Gmail operations
  agent      — orchestration
  database   — skip already-processed message ids
  review     — interactive approve/trash flow
"""

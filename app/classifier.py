"""Email classifier: Ollama (local) or Gemini (API).

Does not write to Gmail. Invalid or forbidden model output becomes UNKNOWN /
NO_ACTION. Connectivity errors are raised so the operator can see the backend is down.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from pydantic import ValidationError

from app.config import (
    GEMINI_API_BASE_URL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from app.models import (
    FORBIDDEN_ACTIONS,
    Action,
    Category,
    ClassificationResult,
    EmailMessage,
    Importance,
)

SYSTEM_PROMPT = """You are an email classification assistant.

Your job is to classify emails based on whether the user is likely to
need attention from them.

IMPORTANT means:
- Personal messages
- Work messages requiring action
- Interview invitations
- Financial/security alerts
- Important account notifications
- Messages containing deadlines
- Messages requiring a response

TO_PROCESS means:
- Marketing
- Newsletters
- Promotional emails
- Social notifications
- Job recommendation emails
- Routine notifications
- Low-value updates

UNKNOWN means:
- You cannot confidently determine the appropriate category.

Safety rules:
- Never classify an email as IMPORTANT solely because the sender is well-known.
- Look at the actual subject and body.
- If uncertain, use UNKNOWN.
- Never recommend deleting an email.

Return ONLY valid JSON matching this schema:
{
  "category": "IMPORTANT" | "TO_PROCESS" | "UNKNOWN",
  "importance": "HIGH" | "MEDIUM" | "LOW",
  "confidence": 0.0 to 1.0,
  "reason": "short explanation",
  "action": "LEAVE_IN_INBOX" | "LABEL_AND_ARCHIVE" | "NO_ACTION"
}

Allowed actions only:
- IMPORTANT -> LEAVE_IN_INBOX
- TO_PROCESS -> LABEL_AND_ARCHIVE
- UNKNOWN -> NO_ACTION

Never return DELETE or MOVE_TO_SPAM.
"""

# Keep prompts bounded so local and API models stay fast/cheap.
_BODY_LIMIT = 2000


class ClassifierError(Exception):
    """Raised when the classifier cannot reach the LLM or get a usable response."""


def _truncate(text: str, limit: int = _BODY_LIMIT) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_user_prompt(email: EmailMessage) -> str:
    """Build the user message sent to the model."""
    return (
        "Classify this email.\n\n"
        f"From: {email.sender}\n"
        f"To: {email.recipient}\n"
        f"Subject: {email.subject}\n"
        f"Date: {email.date}\n"
        f"Snippet: {email.snippet}\n"
        f"Body:\n{_truncate(email.body)}\n"
    )


def unknown_result(reason: str) -> ClassificationResult:
    """Safe fallback when model output cannot be trusted."""
    return ClassificationResult(
        category=Category.UNKNOWN,
        importance=Importance.LOW,
        confidence=0.0,
        reason=reason,
        action=Action.NO_ACTION,
    )


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from model text (tolerates markdown fences)."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model response")
        cleaned = cleaned[start : end + 1]

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Model JSON must be an object")
    return data


def parse_classification(data: dict[str, Any]) -> ClassificationResult:
    """Validate raw model JSON into ClassificationResult."""
    action = data.get("action")
    if isinstance(action, str) and action.upper() in FORBIDDEN_ACTIONS:
        raise ValueError(f"Forbidden action returned by model: {action}")

    return ClassificationResult.model_validate(data)


def call_ollama(
    *,
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 120.0,
) -> str:
    """Call Ollama chat API and return the assistant message content."""
    base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
    model = model or OLLAMA_MODEL
    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ClassifierError(
            f"Could not reach Ollama at {base_url}. "
            "Is Ollama running and is the model pulled?"
        ) from exc

    content = body.get("message", {}).get("content")
    if not content:
        raise ClassifierError("Ollama returned an empty message")
    return str(content)


def call_gemini(
    *,
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 60.0,
) -> str:
    """Call Gemini generateContent and return the first candidate text."""
    api_key = (api_key if api_key is not None else GEMINI_API_KEY).strip()
    if not api_key:
        raise ClassifierError(
            "GEMINI_API_KEY is missing. Create a key at https://aistudio.google.com/apikey "
            "and add it to your local .env."
        )

    model = model or GEMINI_MODEL
    base_url = (base_url or GEMINI_API_BASE_URL).rstrip("/")
    url = f"{base_url}/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ClassifierError(
            f"Gemini HTTP {exc.code} for model {model}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ClassifierError(
            f"Could not reach Gemini at {base_url}. Check network access."
        ) from exc

    parts = (
        body.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(str(part.get("text", "")) for part in parts).strip()
    if not text:
        raise ClassifierError("Gemini returned an empty message")
    return text


def call_llm(
    *,
    prompt: str,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    """Dispatch to the configured LLM provider."""
    current = (provider or LLM_PROVIDER).strip().lower()
    if current == "gemini":
        return call_gemini(
            prompt=prompt,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
    if current == "ollama":
        return call_ollama(prompt=prompt, base_url=base_url, model=model)
    raise ClassifierError(
        f"Unknown LLM_PROVIDER={current!r}. Use ollama or gemini."
    )


def classify(
    email: EmailMessage,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> ClassificationResult:
    """Classify one email and return a validated decision."""
    prompt = build_user_prompt(email)
    try:
        raw_text = call_llm(
            prompt=prompt,
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
        )
        data = extract_json_object(raw_text)
        return parse_classification(data)
    except ClassifierError:
        raise
    except (ValueError, ValidationError, json.JSONDecodeError, TypeError) as exc:
        # Bad JSON / schema → do nothing rather than act on garbage.
        return unknown_result(f"Invalid model output: {exc}")

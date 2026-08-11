"""Agent orchestration layer (Lesson 7).

Fetch → Parse → Classify → Validate → Decide → Execute

Gmail API, parsing, classification, and actions stay in separate modules.
No LangChain / LangGraph.
"""

from __future__ import annotations

from dataclasses import dataclass

from googleapiclient.discovery import Resource

from app.actions import execute_decision, proposed_action
from app.classifier import classify
from app.config import MAX_EMAILS_PER_RUN, MODE
from app.gmail import get_message, get_service, list_messages
from app.models import Action, ClassificationResult, EmailMessage
from app.parser import parse

ALLOWED_ACTIONS = frozenset(
    {
        Action.LEAVE_IN_INBOX,
        Action.LABEL_AND_ARCHIVE,
        Action.NO_ACTION,
    }
)


@dataclass
class AgentResult:
    """One email processed through the agent pipeline."""

    email: EmailMessage
    decision: ClassificationResult
    action: Action
    execution_note: str


class AgentError(Exception):
    """Raised when the agent rejects an invalid decision."""


def validate_decision(decision: ClassificationResult) -> ClassificationResult:
    """Ensure the decision action is on the hard allowlist."""
    action = decision.action
    if action not in ALLOWED_ACTIONS:
        label = action.value if isinstance(action, Action) else str(action)
        raise AgentError(f"Action not allowlisted: {label}")
    return decision


def decide(decision: ClassificationResult) -> Action:
    """Map a validated classification to an allowlisted action."""
    validated = validate_decision(decision)
    action = proposed_action(validated)
    if action not in ALLOWED_ACTIONS:
        raise AgentError(f"Decided action not allowlisted: {action.value}")
    return action


class GmailAgent:
    """Orchestrates the inbox pipeline using existing modules."""

    def __init__(
        self,
        service: Resource | None = None,
        *,
        mode: str | None = None,
        max_emails: int | None = None,
    ) -> None:
        self.service = service
        self.mode = mode or MODE
        self.max_emails = MAX_EMAILS_PER_RUN if max_emails is None else max_emails

    def _ensure_service(self) -> Resource:
        if self.service is None:
            self.service = get_service()
        return self.service

    def fetch_raw_messages(self) -> list[dict]:
        """Fetch recent raw Gmail message dicts."""
        service = self._ensure_service()
        stubs = list_messages(service, max_results=self.max_emails)
        return [get_message(service, stub["id"]) for stub in stubs]

    def process_email(self, raw_message: dict) -> AgentResult:
        """Run parse → classify → validate → decide → execute for one email."""
        email = parse(raw_message)
        decision = validate_decision(classify(email))
        action = decide(decision)
        execution_note = execute_decision(
            decision,
            mode=self.mode,
            service=self._ensure_service(),
            message_id=email.message_id,
        )
        return AgentResult(
            email=email,
            decision=decision,
            action=action,
            execution_note=execution_note,
        )

    def run(self) -> list[AgentResult]:
        """Run the full pipeline over recent emails."""
        results: list[AgentResult] = []
        for raw in self.fetch_raw_messages():
            results.append(self.process_email(raw))
        return results


def run_agent(
    *,
    mode: str | None = None,
    max_emails: int | None = None,
    service: Resource | None = None,
) -> list[AgentResult]:
    """Convenience wrapper used by the CLI."""
    agent = GmailAgent(service=service, mode=mode, max_emails=max_emails)
    return agent.run()

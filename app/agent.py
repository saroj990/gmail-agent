"""Agent orchestration layer (Lessons 7–8).

Fetch → Parse → Classify → Validate → Decide → Execute (via allowlisted tools)

Gmail API, parsing, classification, and actions stay in separate modules.
No LangChain / LangGraph.
"""

from __future__ import annotations

from dataclasses import dataclass

from googleapiclient.discovery import Resource

from app.actions import gmail_writes_allowed, meets_archive_guards, proposed_action
from app.classifier import classify
from app.config import MAX_EMAILS_PER_RUN, MODE
from app.models import Action, ClassificationResult, EmailMessage
from app.tools import GmailTools, ToolError

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
    """Orchestrates the inbox pipeline using allowlisted tools."""

    def __init__(
        self,
        service: Resource | None = None,
        *,
        mode: str | None = None,
        max_emails: int | None = None,
        tools: GmailTools | None = None,
    ) -> None:
        self.service = service
        self.mode = mode or MODE
        self.max_emails = MAX_EMAILS_PER_RUN if max_emails is None else max_emails
        self.tools = tools or GmailTools(service=service)

    def _sync_tools_service(self) -> GmailTools:
        if self.service is not None:
            self.tools.service = self.service
        elif self.tools.service is not None:
            self.service = self.tools.service
        return self.tools

    def fetch_emails(self) -> list[EmailMessage]:
        """Fetch recent emails via tools: get_recent_emails → read_email."""
        tools = self._sync_tools_service()
        stubs = tools.invoke("get_recent_emails", max_results=self.max_emails)
        emails: list[EmailMessage] = []
        for stub in stubs:
            emails.append(tools.invoke("read_email", message_id=stub["id"]))
        if tools.service is not None:
            self.service = tools.service
        return emails

    def fetch_raw_messages(self) -> list[dict]:
        """Compatibility helper used by older CLI helpers."""
        tools = self._sync_tools_service()
        stubs = tools.invoke("get_recent_emails", max_results=self.max_emails)
        from app.gmail import get_message

        service = tools._ensure_service()
        self.service = service
        return [get_message(service, stub["id"]) for stub in stubs]

    def execute(self, email: EmailMessage, decision: ClassificationResult, action: Action) -> str:
        """Execute an allowlisted action using tools only (no invented Gmail ops)."""
        if action not in ALLOWED_ACTIONS:
            raise AgentError(f"Action not allowlisted: {action.value}")

        if not gmail_writes_allowed(self.mode):
            return f"skipped ({self.mode}): {action.value}"

        if action in {Action.LEAVE_IN_INBOX, Action.NO_ACTION}:
            return f"no write: {action.value}"

        if action == Action.LABEL_AND_ARCHIVE:
            allowed, reason = meets_archive_guards(decision, mode=self.mode)
            if not allowed:
                return f"skipped ({reason}): {action.value}"

            tools = self._sync_tools_service()
            label_name = tools.invoke("apply_label", message_id=email.message_id)
            tools.invoke("archive_email", message_id=email.message_id)
            return f"labeled '{label_name}' and archived"

        raise AgentError(f"Unsupported action: {action.value}")

    def process_email(self, email: EmailMessage) -> AgentResult:
        """Run classify → validate → decide → execute for one parsed email."""
        decision = validate_decision(classify(email))
        action = decide(decision)
        execution_note = self.execute(email, decision, action)
        return AgentResult(
            email=email,
            decision=decision,
            action=action,
            execution_note=execution_note,
        )

    def process_raw_email(self, raw_message: dict) -> AgentResult:
        """Parse a raw Gmail dict then process it (test helper)."""
        from app.parser import parse

        return self.process_email(parse(raw_message))

    def run(self) -> list[AgentResult]:
        """Run the full pipeline over recent emails via tools."""
        results: list[AgentResult] = []
        for email in self.fetch_emails():
            results.append(self.process_email(email))
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

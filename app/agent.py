"""Agent orchestration layer (Lessons 7–9).

Fetch → Parse → Classify → Validate → Decide → Execute (via allowlisted tools)

Modes:
- dry_run: report only
- approval: propose and require explicit y/N before writes
- automatic: execute when content guards pass
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from googleapiclient.discovery import Resource

from app.actions import meets_content_guards, proposed_action
from app.classifier import classify
from app.config import GMAIL_LABEL, MAX_EMAILS_PER_RUN, MODE
from app.models import Action, ClassificationResult, EmailMessage
from app.tools import GmailTools

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


def format_proposal(email: EmailMessage, decision: ClassificationResult, action: Action) -> str:
    """Build the Lesson 9 approval prompt text."""
    return (
        f"Email:\n{email.sender} — {email.subject}\n\n"
        f"AI Decision:\n{decision.category.value}\n"
        f"Confidence: {decision.confidence:.2f}\n"
        f"Reason: {decision.reason}\n\n"
        f"Proposed action:\n"
        f"Apply {GMAIL_LABEL!r} and archive\n"
        if action == Action.LABEL_AND_ARCHIVE
        else f"Proposed action:\n{action.value}\n"
    )


def ask_approval(
    email: EmailMessage,
    decision: ClassificationResult,
    action: Action,
    *,
    input_fn: Callable[[str], str] = input,
) -> bool:
    """Ask the user to approve a proposed Gmail write. Default is No."""
    print(format_proposal(email, decision, action))
    answer = input_fn("Approve? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


class GmailAgent:
    """Orchestrates the inbox pipeline using allowlisted tools."""

    def __init__(
        self,
        service: Resource | None = None,
        *,
        mode: str | None = None,
        max_emails: int | None = None,
        tools: GmailTools | None = None,
        input_fn: Callable[[str], str] = input,
    ) -> None:
        self.service = service
        self.mode = (mode or MODE).strip().lower()
        self.max_emails = MAX_EMAILS_PER_RUN if max_emails is None else max_emails
        self.tools = tools or GmailTools(service=service)
        self.input_fn = input_fn

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

    def _perform_label_and_archive(self, email: EmailMessage) -> str:
        tools = self._sync_tools_service()
        label_name = tools.invoke("apply_label", message_id=email.message_id)
        tools.invoke("archive_email", message_id=email.message_id)
        return f"labeled '{label_name}' and archived"

    def execute(self, email: EmailMessage, decision: ClassificationResult, action: Action) -> str:
        """Execute an allowlisted action with mode-aware human approval."""
        if action not in ALLOWED_ACTIONS:
            raise AgentError(f"Action not allowlisted: {action.value}")

        if action in {Action.LEAVE_IN_INBOX, Action.NO_ACTION}:
            return f"no write: {action.value}"

        if self.mode == "dry_run":
            return f"skipped (dry_run): {action.value}"

        if action != Action.LABEL_AND_ARCHIVE:
            raise AgentError(f"Unsupported action: {action.value}")

        allowed, reason = meets_content_guards(decision)
        if not allowed:
            return f"skipped ({reason}): {action.value}"

        if self.mode == "approval":
            if not ask_approval(email, decision, action, input_fn=self.input_fn):
                return f"declined by user: {action.value}"
        elif self.mode != "automatic":
            return f"skipped (mode is {self.mode}): {action.value}"

        return self._perform_label_and_archive(email)

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
    input_fn: Callable[[str], str] = input,
) -> list[AgentResult]:
    """Convenience wrapper used by the CLI."""
    agent = GmailAgent(
        service=service,
        mode=mode,
        max_emails=max_emails,
        input_fn=input_fn,
    )
    return agent.run()

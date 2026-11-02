"""Local HTTP API for the Svelte web UI.

Start with `python main.py serve` (binds to 127.0.0.1 only), or for backend
development `uvicorn app.server:create_app --factory --reload`. Runs execute in a
background thread; the UI polls /api/runs/{id} for progress.

Gmail writes happen only in two places:
- an `automatic` run (same guards as the CLI), or
- POST /api/runs/{id}/apply for rows of a finished dry run the user selected.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.actions import meets_content_guards
from app.agent import AgentError, AgentResult, GmailAgent
from app.classifier import ClassifierError, list_ollama_models
from app.config import GEMINI_API_KEY, MODE, PROJECT_ROOT
from app.database import DecisionStore
from app.gmail import (
    GmailAuthError,
    GmailNotSignedInError,
    get_profile_email,
    get_service,
    run_login_flow_web,
    sign_out,
)
from app.models import Action
from app.settings import Settings, SettingsStore
from app.tools import GmailTools

logger = logging.getLogger(__name__)

WEB_BUILD_DIR = PROJECT_ROOT / "web" / "build"
# adapter-static SPA entry point (see web/vite.config.ts).
SPA_FALLBACK = "200.html"
LOGIN_TIMEOUT_SECONDS = 300
# Custom header the UI sends on writes. Browsers cannot attach it cross-origin
# without a CORS preflight (which this server never approves), blocking CSRF.
CSRF_HEADER = "x-gmail-agent"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _gmail_error_message(exc: HttpError) -> str:
    status = getattr(exc.resp, "status", "?")
    return f"Gmail API error (HTTP {status}): {exc.reason or exc}"


class LoginState:
    """Tracks popup Google sign-in running in a background thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._url_ready = threading.Event()
        self.in_progress = False
        self.error: str | None = None
        self.authorization_url: str | None = None

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self.in_progress:
                return {
                    "login_in_progress": True,
                    "authorization_url": self.authorization_url,
                }
            self.in_progress = True
            self.error = None
            self.authorization_url = None
            self._url_ready.clear()
        threading.Thread(target=self._run, name="gmail-login", daemon=True).start()
        self._url_ready.wait(timeout=10)
        with self._lock:
            return {
                "login_in_progress": True,
                "authorization_url": self.authorization_url,
            }

    def _run(self) -> None:
        error: str | None = None

        def on_url(url: str) -> None:
            with self._lock:
                self.authorization_url = url
            self._url_ready.set()

        try:
            run_login_flow_web(
                on_authorization_url=on_url,
                timeout_seconds=LOGIN_TIMEOUT_SECONDS,
            )
        except GmailAuthError as exc:
            error = str(exc)
        except Exception:
            logger.exception("Unexpected error during Google sign-in")
            error = "Unexpected error during Google sign-in. Check the server log."
        with self._lock:
            self.in_progress = False
            self.error = error
            if not self.authorization_url:
                self._url_ready.set()

    def public_fields(self) -> dict[str, Any]:
        with self._lock:
            return {
                "login_in_progress": self.in_progress,
                "login_error": self.error,
                "authorization_url": self.authorization_url,
            }


@dataclass
class RunItem:
    message_id: str
    sender: str
    subject: str
    date: str
    snippet: str
    category: str
    importance: str
    confidence: float
    reason: str
    action: str
    execution_note: str
    eligible: bool
    applied: bool = False


@dataclass
class RunJob:
    id: str
    mode: str
    settings: Settings
    status: Literal["running", "completed", "failed"] = "running"
    total: int | None = None
    skipped_cached: int = 0
    items: list[RunItem] = field(default_factory=list)
    error: str | None = None
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    results: dict[str, AgentResult] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "status": self.status,
            "total": self.total,
            "processed": len(self.items),
            "skipped_cached": self.skipped_cached,
            "items": [asdict(item) for item in self.items],
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "settings": self.settings.model_dump(),
        }


class RunRequest(BaseModel):
    mode: Literal["dry_run", "automatic"]


class ApplyRequest(BaseModel):
    message_ids: list[str] = Field(min_length=1, max_length=100)


class RunManager:
    """One run at a time; keeps recent jobs in memory for the UI."""

    MAX_JOBS = 10

    def __init__(self, decision_store: DecisionStore) -> None:
        self.store = decision_store
        self._lock = threading.Lock()
        self._apply_lock = threading.Lock()
        self._jobs: dict[str, RunJob] = {}
        self._latest_id: str | None = None

    def snapshot(self, job_id: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id or self._latest_id or "")
            return job.to_dict() if job else None

    def start(self, mode: str, settings: Settings) -> dict[str, Any]:
        with self._lock:
            latest = self._jobs.get(self._latest_id or "")
            if latest and latest.status == "running":
                raise HTTPException(409, "A run is already in progress.")
            job = RunJob(id=uuid.uuid4().hex, mode=mode, settings=settings)
            self._jobs[job.id] = job
            self._latest_id = job.id
            while len(self._jobs) > self.MAX_JOBS:
                self._jobs.pop(next(iter(self._jobs)))
            snapshot = job.to_dict()
        threading.Thread(target=self._run, args=(job,), name="gmail-run", daemon=True).start()
        return snapshot

    def _run(self, job: RunJob) -> None:
        error: str | None = None
        try:
            service = get_service(interactive=False)
            agent = GmailAgent(
                service=service,
                mode=job.mode,
                settings=job.settings,
                store=self.store,
                persist=job.mode != "dry_run",
            )

            def on_fetched(total: int) -> None:
                with self._lock:
                    job.total = total
                    job.skipped_cached = agent.skipped_cached

            def on_result(result: AgentResult) -> None:
                passes, guard_reason = meets_content_guards(
                    result.decision, threshold=job.settings.confidence_threshold
                )
                eligible = passes and result.action == Action.LABEL_AND_ARCHIVE
                note = result.execution_note
                if job.mode == "dry_run" and result.action == Action.LABEL_AND_ARCHIVE:
                    note = (
                        "would label + archive"
                        if eligible
                        else f"would skip ({guard_reason})"
                    )
                item = RunItem(
                    message_id=result.email.message_id,
                    sender=result.email.sender,
                    subject=result.email.subject,
                    date=result.email.date,
                    snippet=result.email.snippet,
                    category=result.decision.category.value,
                    importance=result.decision.importance.value,
                    confidence=result.decision.confidence,
                    reason=result.decision.reason,
                    action=result.action.value,
                    execution_note=note,
                    eligible=eligible,
                )
                with self._lock:
                    job.items.append(item)
                    job.results[item.message_id] = result

            agent.run(on_fetched=on_fetched, on_result=on_result)
        except GmailAuthError as exc:
            error = f"Authentication error: {exc}"
        except ClassifierError as exc:
            error = f"Classifier error: {exc}"
        except HttpError as exc:
            error = _gmail_error_message(exc)
        except AgentError as exc:
            error = f"Agent error: {exc}"
        except Exception as exc:
            logger.exception("Run %s failed", job.id)
            error = f"Unexpected error: {exc}"
        with self._lock:
            job.error = error
            job.status = "failed" if error else "completed"
            job.finished_at = _now()

    def apply(self, job_id: str, message_ids: list[str]) -> dict[str, Any]:
        """Label + archive user-approved rows from a finished dry run."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise HTTPException(404, "Run not found (the server may have restarted).")
            if job.mode != "dry_run" or job.status != "completed":
                raise HTTPException(409, "Only a completed dry run can be applied.")

        try:
            service = get_service(interactive=False)
        except GmailAuthError as exc:
            raise HTTPException(401, str(exc)) from exc
        tools = GmailTools(service=service)
        items = {item.message_id: item for item in job.items}

        with self._apply_lock:
            for message_id in dict.fromkeys(message_ids):
                item = items.get(message_id)
                result = job.results.get(message_id)
                if item is None or result is None or item.applied:
                    continue
                allowed, reason = meets_content_guards(
                    result.decision, threshold=job.settings.confidence_threshold
                )
                if result.action != Action.LABEL_AND_ARCHIVE or not allowed:
                    note = f"skipped ({reason})"
                    applied = False
                else:
                    try:
                        label = tools.invoke(
                            "apply_label",
                            message_id=message_id,
                            label_name=job.settings.gmail_label,
                        )
                        tools.invoke("archive_email", message_id=message_id)
                        note = f"labeled '{label}' and archived (approved in web UI)"
                        applied = True
                    except HttpError as exc:
                        note = f"failed: {_gmail_error_message(exc)}"
                        applied = False
                if applied:
                    self.store.save_decision(
                        result.email,
                        result.decision,
                        action=result.action.value,
                        execution_note=note,
                    )
                with self._lock:
                    item.execution_note = note
                    item.applied = applied

        return self.snapshot(job_id) or {}


def create_app(
    *,
    settings_store: SettingsStore | None = None,
    decision_store: DecisionStore | None = None,
    static_dir: Path | None = WEB_BUILD_DIR,
) -> FastAPI:
    settings_store = settings_store or SettingsStore()
    decision_store = decision_store or DecisionStore()
    login = LoginState()
    runs = RunManager(decision_store)

    app = FastAPI(title="Gmail AI Inbox Agent", docs_url="/api/docs", openapi_url="/api/openapi.json")
    # Rejects DNS-rebinding requests that reach 127.0.0.1 under a foreign hostname.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

    @app.middleware("http")
    async def require_csrf_header(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method not in SAFE_METHODS:
            if request.headers.get(CSRF_HEADER) != "1":
                return JSONResponse(
                    {"detail": f"Missing {CSRF_HEADER} header."}, status_code=403
                )
        return await call_next(request)

    def settings_payload(settings: Settings) -> dict[str, Any]:
        return {
            "settings": settings.model_dump(),
            "gemini_api_key_configured": bool(GEMINI_API_KEY),
            "cli_mode": MODE,
        }

    @app.get("/api/auth/status")
    def auth_status() -> dict[str, Any]:
        status: dict[str, Any] = {
            "signed_in": False,
            "email": None,
            "error": None,
            **login.public_fields(),
        }
        try:
            service = get_service(interactive=False)
            status["email"] = get_profile_email(service)
            status["signed_in"] = True
        except GmailNotSignedInError:
            pass
        except GmailAuthError as exc:
            status["error"] = str(exc)
        except HttpError as exc:
            status["error"] = _gmail_error_message(exc)
        return status

    @app.post("/api/auth/login", status_code=202)
    def auth_login() -> dict[str, Any]:
        body = login.start()
        if not body.get("authorization_url"):
            raise HTTPException(
                503,
                "Could not start Google sign-in. Check credentials.json and try again.",
            )
        return body

    @app.post("/api/auth/logout")
    def auth_logout() -> dict[str, Any]:
        sign_out()
        return {"signed_in": False}

    @app.get("/api/settings")
    def read_settings() -> dict[str, Any]:
        return settings_payload(settings_store.load())

    @app.put("/api/settings")
    def write_settings(settings: Settings) -> dict[str, Any]:
        return settings_payload(settings_store.save(settings))

    @app.post("/api/settings/reset")
    def reset_settings() -> dict[str, Any]:
        return settings_payload(settings_store.reset())

    @app.get("/api/ollama/models")
    def ollama_models(base_url: str | None = None) -> dict[str, Any]:
        url = base_url or settings_store.load().ollama_base_url
        try:
            return {"models": list_ollama_models(url)}
        except ClassifierError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.post("/api/runs", status_code=202)
    def start_run(body: RunRequest) -> dict[str, Any]:
        return runs.start(body.mode, settings_store.load())

    @app.get("/api/runs/latest")
    def latest_run() -> dict[str, Any] | None:
        return runs.snapshot()

    @app.get("/api/runs/{job_id}")
    def get_run(job_id: str) -> dict[str, Any]:
        snapshot = runs.snapshot(job_id)
        if snapshot is None:
            raise HTTPException(404, "Run not found (the server may have restarted).")
        return snapshot

    @app.post("/api/runs/{job_id}/apply")
    def apply_run(job_id: str, body: ApplyRequest) -> dict[str, Any]:
        return runs.apply(job_id, body.message_ids)

    @app.get("/api/history")
    def history(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
        from app.database import utc_today_start_iso

        return {
            "items": decision_store.recent(limit),
            "total": decision_store.count(),
            "processed_today": decision_store.count_since(utc_today_start_iso()),
        }

    if static_dir is not None and (static_dir / SPA_FALLBACK).exists():
        root = static_dir.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404, "Not found")
            candidate = (root / path).resolve()
            if path and candidate.is_file() and root in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(root / SPA_FALLBACK)

    return app

"""Tests for the web UI HTTP API."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import DecisionStore
from app.gmail import GmailAuthError, GmailNotSignedInError
from app.models import Action, Category, ClassificationResult, EmailMessage, Importance
from app.server import create_app
from app.settings import SettingsStore

HEADERS = {"X-Gmail-Agent": "1"}


@pytest.fixture
def store(tmp_path) -> DecisionStore:
    return DecisionStore(db_path=tmp_path / "decisions.db")


@pytest.fixture
def client(tmp_path, store) -> TestClient:
    app = create_app(
        settings_store=SettingsStore(tmp_path / "settings.json"),
        decision_store=store,
        static_dir=None,
    )
    return TestClient(app, base_url="http://localhost")


def _decision(category: Category, confidence: float) -> ClassificationResult:
    return ClassificationResult(
        category=category,
        importance=Importance.LOW,
        confidence=confidence,
        reason="test",
        action=Action.NO_ACTION,
    )


def _wait_for_run(client: TestClient, run_id: str) -> dict:
    for _ in range(200):
        body = client.get(f"/api/runs/{run_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.01)
    raise AssertionError("run did not finish")


def test_write_without_csrf_header_is_rejected(client) -> None:
    response = client.post("/api/auth/logout")
    assert response.status_code == 403


def test_foreign_host_header_is_rejected(client) -> None:
    response = client.get("/api/settings", headers={"Host": "evil.example"})
    assert response.status_code == 400


def test_settings_round_trip_and_validation(client) -> None:
    current = client.get("/api/settings").json()["settings"]
    updated = {**current, "confidence_threshold": 0.8, "gmail_label": "Later"}

    response = client.put("/api/settings", json=updated, headers=HEADERS)
    assert response.status_code == 200
    assert client.get("/api/settings").json()["settings"]["gmail_label"] == "Later"

    bad = client.put(
        "/api/settings", json={**current, "confidence_threshold": 2}, headers=HEADERS
    )
    assert bad.status_code == 422


def test_auth_status_reports_expired_login_error(client) -> None:
    with patch(
        "app.server.get_service",
        side_effect=GmailAuthError("Saved Gmail login is no longer valid"),
    ):
        body = client.get("/api/auth/status").json()
    assert body["signed_in"] is False
    assert "no longer valid" in body["error"]


def test_auth_status_not_signed_in_has_no_error(client) -> None:
    with patch("app.server.get_service", side_effect=GmailNotSignedInError("nope")):
        body = client.get("/api/auth/status").json()
    assert body == {
        "signed_in": False,
        "email": None,
        "error": None,
        "login_in_progress": False,
        "login_error": None,
        "authorization_url": None,
    }


def test_auth_login_returns_authorization_url(client) -> None:
    def fake_web(*, on_authorization_url, timeout_seconds):
        on_authorization_url("https://accounts.google.com/o/oauth2/auth?test=1")
        from google.oauth2.credentials import Credentials

        return Credentials(token="x")

    with patch("app.server.run_login_flow_web", side_effect=fake_web):
        body = client.post("/api/auth/login", headers=HEADERS).json()
    assert body["login_in_progress"] is True
    assert body["authorization_url"].startswith("https://accounts.google.com/")


def test_auth_status_signed_in(client) -> None:
    with (
        patch("app.server.get_service", return_value=MagicMock()),
        patch("app.server.get_profile_email", return_value="me@example.com"),
    ):
        body = client.get("/api/auth/status").json()
    assert body["signed_in"] is True
    assert body["email"] == "me@example.com"


def test_run_reports_auth_failure(client) -> None:
    with patch("app.server.get_service", side_effect=GmailAuthError("expired")):
        run = client.post("/api/runs", json={"mode": "dry_run"}, headers=HEADERS).json()
        result = _wait_for_run(client, run["id"])
    assert result["status"] == "failed"
    assert result["error"] == "Authentication error: expired"


def test_dry_run_then_apply_selected(client, store) -> None:
    emails = {
        "promo": EmailMessage(message_id="promo", thread_id="t1", subject="Sale"),
        "boss": EmailMessage(message_id="boss", thread_id="t2", subject="Review"),
    }
    decisions = {
        "promo": _decision(Category.TO_PROCESS, 0.99),
        "boss": _decision(Category.IMPORTANT, 0.99),
    }

    with (
        patch("app.server.get_service", return_value=MagicMock()),
        patch(
            "app.agent.collect_unprocessed_stubs",
            return_value=(
                [{"id": "promo", "threadId": "t1"}, {"id": "boss", "threadId": "t2"}],
                0,
            ),
        ),
        patch("app.tools.get_message", side_effect=lambda _s, mid: {"id": mid}),
        patch("app.tools.parse", side_effect=lambda raw: emails[raw["id"]]),
        patch("app.agent.classify", side_effect=lambda email, **_: decisions[email.message_id]),
        patch("app.tools.apply_to_process_label", return_value="Later") as mock_label,
        patch("app.tools.archive_message") as mock_archive,
    ):
        run = client.post("/api/runs", json={"mode": "dry_run"}, headers=HEADERS).json()
        result = _wait_for_run(client, run["id"])

        assert result["status"] == "completed"
        assert result["total"] == 2
        items = {item["message_id"]: item for item in result["items"]}
        assert items["promo"]["eligible"] is True
        assert items["promo"]["execution_note"] == "would label + archive"
        assert items["boss"]["eligible"] is False
        # Dry runs leave memory untouched so a real run still sees these emails.
        assert store.count() == 0
        mock_label.assert_not_called()

        applied = client.post(
            f"/api/runs/{run['id']}/apply",
            json={"message_ids": ["promo", "boss"]},
            headers=HEADERS,
        ).json()

    items = {item["message_id"]: item for item in applied["items"]}
    assert items["promo"]["applied"] is True
    assert items["boss"]["applied"] is False
    assert "category is IMPORTANT" in items["boss"]["execution_note"]
    mock_label.assert_called_once()
    mock_archive.assert_called_once()
    assert store.has_message("promo") is True
    assert store.has_message("boss") is False


def test_apply_rejects_automatic_run(client) -> None:
    with (
        patch("app.server.get_service", return_value=MagicMock()),
        patch("app.agent.collect_unprocessed_stubs", return_value=([], 0)),
    ):
        run = client.post("/api/runs", json={"mode": "automatic"}, headers=HEADERS).json()
        _wait_for_run(client, run["id"])
        response = client.post(
            f"/api/runs/{run['id']}/apply", json={"message_ids": ["x"]}, headers=HEADERS
        )
    assert response.status_code == 409


def test_history_lists_saved_decisions(client, store) -> None:
    store.save_decision(
        EmailMessage(message_id="m1", thread_id="t", subject="Hello"),
        _decision(Category.TO_PROCESS, 0.97),
        execution_note="labeled",
    )
    body = client.get("/api/history").json()
    assert body["total"] == 1
    assert body["items"][0]["subject"] == "Hello"

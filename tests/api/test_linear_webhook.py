"""Tests for the Linear webhook receiver (issue #242)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("DASHBOARD_API_KEY", "test-key")

import server  # noqa: E402
from routers import linear_webhook as webhook_router  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app)


@pytest.fixture(autouse=True)
def _clear_replay_buffer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts with a clean replay buffer."""
    webhook_router._processed_webhook_ids.clear()


# ─── Payload helpers ───────────────────────────────────────────────────────────


def _make_payload(
    *,
    action: str = "create",
    type_: str = "Issue",
    data: dict | None = None,
    created_at: int | str | None = None,
    webhook_id: str | None = "webhook-123",
    organization_id: str | None = "org-456",
) -> dict:
    """Build a minimal Linear webhook payload."""
    if created_at is None:
        # Default to now in milliseconds
        created_at = int(time.time() * 1000)
    return {
        "action": action,
        "type": type_,
        "data": data or {},
        "createdAt": created_at,
        "webhookId": webhook_id,
        "organizationId": organization_id,
    }


def _sign_body(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 hex digest for the Linear-Signature header."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


# ─── Validation tests ──────────────────────────────────────────────────────────


def test_webhook_returns_ok_for_valid_payload(client: TestClient) -> None:
    payload = _make_payload()
    response = client.post(
        "/api/linear/webhook",
        json=payload,
        # No Linear-Signature header sent — dev mode allows this
    )
    # 200 because we skip verification when no header and no secret
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["action"] == "create"
    assert data["type"] == "issue"


def test_webhook_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/api/linear/webhook",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON body"


def test_webhook_rejects_unsupported_action(client: TestClient) -> None:
    payload = _make_payload(action="destroy")
    response = client.post("/api/linear/webhook", json=payload)
    assert response.status_code == 422


def test_webhook_accepts_unknown_type_with_warning(client: TestClient) -> None:
    payload = _make_payload(type_="UnknownType")
    response = client.post("/api/linear/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["type"] == "unknowntype"


# ─── Signature verification tests ─────────────────────────────────────────────


def test_webhook_verifies_signature_with_secret(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "super-secret"
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", secret)

    payload = _make_payload()
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = _sign_body(body, secret)

    response = client.post(
        "/api/linear/webhook",
        content=body,
        headers={"Linear-Signature": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_webhook_rejects_bad_signature(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "super-secret"
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", secret)

    payload = _make_payload()
    response = client.post(
        "/api/linear/webhook",
        json=payload,
        headers={"Linear-Signature": "bad-signature"},
    )
    assert response.status_code == 401


def test_webhook_allows_dev_mode_when_no_secret_or_header(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)
    payload = _make_payload()
    response = client.post("/api/linear/webhook", json=payload)
    assert response.status_code == 200


# ─── Replay protection tests ──────────────────────────────────────────────────


def test_webhook_detects_replay(client: TestClient) -> None:
    payload = _make_payload(webhook_id="replay-me")
    # First request succeeds
    response1 = client.post("/api/linear/webhook", json=payload)
    assert response1.status_code == 200
    assert response1.json().get("replay") is None

    # Second request with same webhookId is flagged as replay
    response2 = client.post("/api/linear/webhook", json=payload)
    assert response2.status_code == 200
    assert response2.json()["replay"] is True


def test_webhook_without_webhook_id_allows_replay(client: TestClient) -> None:
    payload = _make_payload(webhook_id=None)
    response1 = client.post("/api/linear/webhook", json=payload)
    assert response1.status_code == 200

    response2 = client.post("/api/linear/webhook", json=payload)
    assert response2.status_code == 200


# ─── Age check tests ───────────────────────────────────────────────────────────


def test_webhook_rejects_old_payload(client: TestClient) -> None:
    old_time = int((time.time() - 400) * 1000)  # 400 seconds ago, in ms
    payload = _make_payload(created_at=old_time)
    response = client.post("/api/linear/webhook", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Payload too old"


def test_webhook_accepts_recent_payload(client: TestClient) -> None:
    recent_time = int((time.time() - 10) * 1000)  # 10 seconds ago, in ms
    payload = _make_payload(created_at=recent_time)
    response = client.post("/api/linear/webhook", json=payload)
    assert response.status_code == 200


# ─── Health endpoint tests ─────────────────────────────────────────────────────


def test_webhook_health_returns_status(client: TestClient) -> None:
    response = client.get("/api/linear/webhook/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["signature_verification"] == "disabled"
    assert data["max_age_seconds"] == 300
    assert "replay_buffer_size" in data


def test_webhook_health_shows_enabled_when_secret_set(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "some-secret")
    response = client.get("/api/linear/webhook/health")
    assert response.status_code == 200
    assert response.json()["signature_verification"] == "enabled"


# ─── CSRF exemption test ───────────────────────────────────────────────────────


def test_webhook_bypasses_csrf_check(client: TestClient) -> None:
    """The /api/linear/webhook route must NOT require X-Requested-With."""
    payload = _make_payload()
    response = client.post(
        "/api/linear/webhook",
        json=payload,
        headers={"Content-Type": "application/json"},  # No X-Requested-With
    )
    assert response.status_code == 200


def test_other_linear_routes_still_require_csrf(client: TestClient) -> None:
    """Other /api/linear/* routes should still require CSRF for state-changing methods."""
    response = client.post("/api/linear/workspaces", json={})
    # Should get 403 because no X-Requested-With header
    assert response.status_code == 403

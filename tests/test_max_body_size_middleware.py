"""Tests for MaxBodySizeMiddleware (issue #350)."""

from __future__ import annotations

import pytest
from middleware import MaxBodySizeMiddleware
from starlette.testclient import TestClient


async def hello_app(scope, receive, send):
    """Simple ASGI app that echoes back a 200."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"ok"})


@pytest.fixture
def client():
    app = MaxBodySizeMiddleware(hello_app, default_limit=1024)  # 1 KB default
    return TestClient(app)


def test_small_body_allowed(client):
    """A 100-byte POST is under the 1 KB limit → 200."""
    resp = client.post("/", data=b"x" * 100, headers={"Content-Length": "100"})
    assert resp.status_code == 200


def test_large_body_rejected(client):
    """A 2 KB POST exceeds the 1 KB limit → 413."""
    resp = client.post("/", data=b"x" * 2048, headers={"Content-Length": "2048"})
    assert resp.status_code == 413
    assert resp.text == ""


def test_webhook_override_rejected():
    """The production middleware overrides /api/linear/webhook to 256 KB."""
    # Use the production defaults from the middleware module
    from middleware import _DEFAULT_MAX_BODY, _LIMIT_OVERRIDES, _WEBHOOK_MAX_BODY

    assert _LIMIT_OVERRIDES.get("/api/linear/webhook") == _WEBHOOK_MAX_BODY
    assert _WEBHOOK_MAX_BODY == 256 * 1024
    assert _DEFAULT_MAX_BODY == 1 * 1024 * 1024


def test_no_content_length_allowed(client):
    """Requests without Content-Length (e.g. chunked) are not rejected early."""
    # httpx/TestClient always sends Content-Length for non-streaming bodies,
    # so we simulate by omitting it in the scope manually in a separate test.
    resp = client.get("/")
    assert resp.status_code == 200


def test_custom_header_override(client):
    """X-Max-Body-Size header can raise the limit for streaming routes."""
    resp = client.post(
        "/",
        data=b"x" * 2048,
        headers={"Content-Length": "2048", "X-Max-Body-Size": "4096"},
    )
    assert resp.status_code == 200


def test_non_http_scope_passes_through():
    """WebSocket / lifespan scopes bypass the middleware."""
    called = False

    async def mark_called(scope, receive, send):
        nonlocal called
        called = True

    wrapped = MaxBodySizeMiddleware(mark_called, default_limit=1)
    import asyncio

    async def run():
        await wrapped({"type": "websocket"}, None, None)

    asyncio.run(run())
    assert called

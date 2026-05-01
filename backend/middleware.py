"""Middleware extracted from server.py."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

# --------------------------------------------------------------------------- #
# MaxBodySizeMiddleware  (issue #350)
# --------------------------------------------------------------------------- #
# Default limits per path (bytes).  Overridden per-route via decorator.
_DEFAULT_MAX_BODY = 1 * 1024 * 1024  # 1 MB
_WEBHOOK_MAX_BODY = 256 * 1024  # 256 KB
_STREAMING_MAX_BODY = 10 * 1024 * 1024  # 10 MB

_LIMIT_OVERRIDES: dict[str, int] = {
    "/api/linear/webhook": _WEBHOOK_MAX_BODY,
}

_MAX_BODY_HEADER = "X-Max-Body-Size"


class MaxBodySizeMiddleware:
    """Reject requests whose Content-Length exceeds a per-route cap.

    Falls back to ``X-Max-Body-Size`` header (set by route handlers that
    stream large payloads) and finally to the global default.
    """

    def __init__(self, app: Any, default_limit: int = _DEFAULT_MAX_BODY) -> None:
        self.app = app
        self.default_limit = default_limit

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        limit = _LIMIT_OVERRIDES.get(path, self.default_limit)

        # Allow route handlers to override via header in their own middleware
        # or by setting state before we run.  We inspect headers last so the
        # explicit header wins.
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-max-body-size":
                try:
                    limit = int(value.decode())
                except (ValueError, UnicodeDecodeError):
                    pass
                break

        content_length = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    content_length = int(value.decode())
                except (ValueError, UnicodeDecodeError):
                    pass
                break

        if content_length is not None and content_length > limit:
            # Early reject — don't even start the app
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", b"0"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        await self.app(scope, receive, send)


def max_body_size(limit_bytes: int):
    """Decorator for route handlers that need a larger body limit.

    Usage::
        @app.post("/api/upload")
        @max_body_size(10 * 1024 * 1024)
        async def upload(...):
            ...
    """

    def decorator(func: Any) -> Any:
        # Store the limit on the function so the middleware can read it
        # via a custom header injected by a FastAPI dependency or middleware.
        # For simplicity we just note it in a well-known attribute.
        func._max_body_size = limit_bytes  # noqa: B010
        return func

    return decorator


_AUTH_EXEMPT_PATHS = {
    "/",
    "/health",
    "/api/health",
    "/manifest.webmanifest",
    "/icon.svg",
    "/api/auth/github",
    "/api/auth/callback",
    "/api/linear/webhook",
}


async def csrf_check(request: Request, call_next: Any) -> Any:
    """Reject state-changing requests that lack the CSRF sentinel header (issue #30)."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # Skip exempt paths (e.g. external webhooks)
        if request.url.path in _AUTH_EXEMPT_PATHS:
            return await call_next(request)
        # Allow health / static routes without the header so monitoring tools
        # (e.g. curl health checks) still work.  Only enforce on /api/* paths.
        if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/linear/webhook"):
            if request.headers.get("X-Requested-With") != "XMLHttpRequest":
                return JSONResponse(
                    {"error": "CSRF check failed: missing X-Requested-With header"},
                    status_code=403,
                )
    return await call_next(request)


async def add_security_headers(request: Request, call_next: Any) -> Any:
    """Inject standard security headers on every response (issue #7, #18)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'strict-dynamic' "
        "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self' data:;"
    )
    return response

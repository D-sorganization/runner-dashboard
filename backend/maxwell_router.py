# ruff: noqa: B008
"""Maxwell-Daemon proxy routes.

Provides API endpoints to probe, control, and proxy requests to the
Maxwell-Daemon service running on the same host (or a configured URL).

Extracted from server.py as part of epic #159 (god-module refactor).
"""

from __future__ import annotations

import logging
import os
import subprocess

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from identity import Principal, require_scope

log = logging.getLogger("dashboard")

router = APIRouter(prefix="/api/maxwell", tags=["maxwell"])

# ─── Dashboard FAQ (used by /api/help/chat) ───────────────────────────────────
# Kept here alongside the Maxwell tab entry so the FAQ dict lives near its routes.

DASHBOARD_FAQ: dict[str, str] = {
    "fleet": "The Fleet tab shows all runners in your fleet. Use it to start/stop runners and see hardware metrics.",
    "remediation": (
        "The Remediation tab lets you dispatch AI agents (Jules, Codex, Claude) to fix failing CI."
        " Move to top: Manual Dispatch is the primary control."
    ),
    "workflows": (
        "The Workflows tab lists all GitHub Actions workflows across repos."
        " Click a workflow to see run history and dispatch it manually."
    ),
    "credentials": (
        "The Credentials tab shows provider connection state."
        " No secrets are shown - only whether tools are installed and authenticated."
    ),
    "assessments": (
        "The Assessments tab lets you trigger code quality assessments for any repo and view score history."
    ),
    "feature-requests": (
        "The Feature Requests tab dispatches AI agents to implement new features"
        " with standards injection (TDD, DbC, DRY, LoD)."
    ),
    "maxwell": ("The Maxwell tab shows Maxwell-Daemon status and lets you start/stop the service with confirmation."),
    "queue": "The Queue tab shows live queued and in-progress workflows with auto-refresh every 15 seconds.",
    "history": "The History tab shows recent workflow runs across all repos, filterable by status.",
    "machines": "The Machines tab shows hardware telemetry for each fleet node.",
    "stats": "The Stats tab shows P50/P95 duration analytics and success rates across workflows.",
    "runner-plan": "The Runner Plan tab manages day/night runner capacity scheduling.",
    "dispatch": (
        "To dispatch a remediation agent: go to Remediation tab, select a failed run,"
        " choose a provider, preview the plan, then dispatch."
    ),
    "provider": (
        "Providers are AI agents: Jules API (cloud, Google), Codex CLI (OpenAI),"
        " Claude Code CLI (Anthropic), Ollama (local)."
    ),
    "loop guard": (
        "Loop guard prevents infinite retry loops. When the same failure repeats more than"
        " max_same_failure_attempts times, dispatch is blocked."
    ),
}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _maxwell_base_url() -> str:
    """Return the Maxwell-Daemon base URL from env."""
    return os.environ.get("MAXWELL_URL", "") or f"http://localhost:{int(os.environ.get('MAXWELL_PORT', 8322))}"


def _safe_subprocess_env() -> dict[str, str]:
    """Return os.environ with secrets stripped out for subprocess calls."""
    excluded = {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "ANTHROPIC_API_KEY",
        "DASHBOARD_API_KEY",
        "SECRET",
        "PASSWORD",
        "TOKEN",
    }
    return {k: v for k, v in os.environ.items() if not any(exc in k.upper() for exc in excluded)}


# Injected by server.py after app creation so the router can call run_cmd.
_run_cmd = None  # type: ignore[assignment]
_REPO_ROOT = None  # type: ignore[assignment]


def configure(run_cmd_fn, repo_root):
    """Inject shared helpers from server.py (called during startup)."""
    global _run_cmd, _REPO_ROOT  # noqa: PLW0603
    _run_cmd = run_cmd_fn
    _REPO_ROOT = repo_root


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.get("/status")
async def get_maxwell_status() -> dict:
    """Probe Maxwell-Daemon status and connectivity."""
    import datetime as _dt_mod

    UTC = getattr(_dt_mod, "UTC", _dt_mod.timezone.utc)  # noqa: UP017
    datetime = _dt_mod.datetime

    maxwell_binary = __import__("shutil").which("maxwell") or __import__("shutil").which("maxwell-daemon")
    maxwell_url = os.environ.get("MAXWELL_URL", "")
    maxwell_port = int(os.environ.get("MAXWELL_PORT", 8322))

    # Check if maxwell service is running via systemd
    service_running = False
    service_detail = "unknown"
    try:
        r = subprocess.run(
            ["systemctl", "is-active", "maxwell-daemon"],
            capture_output=True,
            text=True,
            timeout=5,
            env=_safe_subprocess_env(),
        )
        if r.returncode == 0 and r.stdout.strip() == "active":
            service_running = True
            service_detail = "systemd service active"
        else:
            service_detail = r.stdout.strip() or "not active"
    except Exception:  # noqa: BLE001
        service_detail = "systemd probe failed"

    # Check HTTP reachability
    http_reachable = False
    http_detail = ""
    base_url = maxwell_url or f"http://localhost:{maxwell_port}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/api/health")
            http_reachable = resp.status_code == 200
            http_detail = f"HTTP {resp.status_code}"
    except Exception as e:  # noqa: BLE001
        http_detail = str(e)[:80]

    status = "running" if (service_running or http_reachable) else "stopped"

    return {
        "status": status,
        "binary_found": maxwell_binary is not None,
        "binary_path": maxwell_binary,
        "service_running": service_running,
        "service_detail": service_detail,
        "http_reachable": http_reachable,
        "http_detail": http_detail,
        "dashboard_url": base_url,
        "deep_links": {
            "dashboard": base_url,
            "health": f"{base_url}/api/health",
            "logs": "journalctl -u maxwell-daemon -f",
        },
        "probed_at": datetime.now(UTC).isoformat(),
    }


@router.post("/control")
async def maxwell_control(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("maxwell.control")),
) -> dict:
    """Start or stop Maxwell-Daemon service (confirmation required)."""
    import shlex

    body = await request.json()
    action = str(body.get("action", "")).strip()
    approved_by = str(body.get("approved_by", "")).strip()
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=422, detail="action must be start, stop, or restart")
    if not approved_by:
        raise HTTPException(status_code=422, detail="approved_by required for privileged action")

    sanitized_action = action.replace("\n", "\\n").replace("\r", "\\r")[:200]
    sanitized_approved_by = approved_by.replace("\n", "\\n").replace("\r", "\\r")[:200]

    code, out, stderr = await _run_cmd(["systemctl", action, "maxwell-daemon"], timeout=15, cwd=_REPO_ROOT)
    log.info(
        "maxwell_control: action=%s approved_by=%s exit_code=%d",
        sanitized_action,
        sanitized_approved_by,
        code,
    )
    if code != 0:
        log.warning("maxwell %s failed: %s", action, stderr.strip()[:200])
        raise HTTPException(
            status_code=502,
            detail=f"maxwell {action} failed",
        )
    return {"status": action + "ed", "action": action, "approved_by": approved_by}


@router.get("/version")
async def get_maxwell_version() -> dict:
    """Proxy GET /api/version from Maxwell-Daemon."""
    path = "/api/version"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{_maxwell_base_url()}{path}")
            log.info("maxwell_proxy: path=%s status=%s", path, resp.status_code)
            return resp.json()
    except Exception as e:  # noqa: BLE001
        log.info("maxwell_proxy: path=%s status=%s", path, "error")
        return {"error": str(e)[:120], "daemon_available": False}


@router.get("/daemon-status")
async def get_maxwell_daemon_status_detail() -> dict:
    """Proxy GET /api/status from Maxwell-Daemon (pipeline state)."""
    path = "/api/status"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{_maxwell_base_url()}{path}")
            log.info("maxwell_proxy: path=%s status=%s", path, resp.status_code)
            return resp.json()
    except Exception as e:  # noqa: BLE001
        log.info("maxwell_proxy: path=%s status=%s", path, "error")
        return {"error": str(e)[:120], "daemon_available": False}


@router.get("/tasks")
async def get_maxwell_tasks(limit: int = 20, cursor: str | None = None) -> dict:
    """Proxy GET /api/tasks from Maxwell-Daemon."""
    path = "/api/tasks"
    try:
        params: dict = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{_maxwell_base_url()}{path}", params=params)
            log.info("maxwell_proxy: path=%s status=%s", path, resp.status_code)
            return resp.json()
    except Exception as e:  # noqa: BLE001
        log.info("maxwell_proxy: path=%s status=%s", path, "error")
        return {"error": str(e)[:120], "daemon_available": False}


@router.get("/tasks/{task_id}")
async def get_maxwell_task_detail(task_id: str) -> dict:
    """Proxy GET /api/tasks/{task_id} from Maxwell-Daemon."""
    path = f"/api/tasks/{task_id}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{_maxwell_base_url()}{path}")
            log.info("maxwell_proxy: path=%s status=%s", path, resp.status_code)
            return resp.json()
    except Exception as e:  # noqa: BLE001
        log.info("maxwell_proxy: path=%s status=%s", path, "error")
        return {"error": str(e)[:120], "daemon_available": False}


@router.post("/dispatch")
async def maxwell_dispatch_task(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("maxwell.control")),
) -> dict:
    """Proxy POST /api/dispatch to Maxwell-Daemon (forwards body as-is)."""
    path = "/api/dispatch"
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{_maxwell_base_url()}{path}",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            log.info("maxwell_proxy: path=%s status=%s", path, resp.status_code)
            return resp.json()
    except Exception as e:  # noqa: BLE001
        log.info("maxwell_proxy: path=%s status=%s", path, "error")
        return {"error": str(e)[:120], "daemon_available": False}


@router.post("/pipeline-control/{action}")
async def maxwell_pipeline_control(
    action: str,
    request: Request,
    *,
    principal: Principal = Depends(require_scope("maxwell.control")),
) -> dict:
    """Proxy POST /api/control/{action} to Maxwell-Daemon."""
    if action not in ("pause", "resume", "abort"):
        raise HTTPException(status_code=422, detail="action must be pause, resume, or abort")
    path = f"/api/control/{action}"
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{_maxwell_base_url()}{path}",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            log.info("maxwell_proxy: path=%s status=%s", path, resp.status_code)
            return resp.json()
    except Exception as e:  # noqa: BLE001
        log.info("maxwell_proxy: path=%s status=%s", path, "error")
        return {"error": str(e)[:120], "daemon_available": False}

# ruff: noqa: B008
"""Diagnostics, launcher-generation, and runner-routing-audit routes.

Provides API endpoints for:
- Deployment git-drift detection (/api/deployment/git-drift)
- Dashboard diagnostics summary (/api/diagnostics/summary)
- Service restart (/api/diagnostics/restart-service)
- Windows launcher script generation (/api/launchers/generate)
- Hosted-runner billing audit (/api/runner-routing-audit)

Extracted from server.py as part of epic #159 (god-module refactor).
"""

from __future__ import annotations

import asyncio
import datetime as _dt_mod
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx
import psutil
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from identity import Principal, require_scope

UTC = getattr(_dt_mod, "UTC", _dt_mod.timezone.utc)  # noqa: UP017
datetime = _dt_mod.datetime

log = logging.getLogger("dashboard")

router = APIRouter(tags=["diagnostics"])

# ─── Hosted-runner billing audit patterns ────────────────────────────────────

HOSTED_RUNNER_PATTERNS = re.compile(
    r"^(ubuntu-|windows-|macos-|GitHub Actions \d|Hosted Agent)",
    re.IGNORECASE,
)

_runner_audit_cache: dict[str, Any] = {"violations": [], "last_checked": None, "error": None}
_runner_audit_lock = asyncio.Lock()

# ─── Injected shared config (set via configure()) ────────────────────────────

_PORT: int = 8321
_SYSTEMCTL_BIN: str = "/usr/bin/systemctl"
_ORG: str = ""
_REPO_ROOT: Path | None = None


def configure(port: int, systemctl_bin: str, org: str, repo_root: Path) -> None:
    """Inject shared config from server.py (called during startup)."""
    global _PORT, _SYSTEMCTL_BIN, _ORG, _REPO_ROOT  # noqa: PLW0603
    _PORT = port
    _SYSTEMCTL_BIN = systemctl_bin
    _ORG = org
    _REPO_ROOT = repo_root


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _fetch_git_drift() -> dict:
    """Return git-commit-based drift data (shared with diagnostics summary)."""
    repo_root = _REPO_ROOT or Path(__file__).parent.parent
    result: dict[str, object] = {}

    source = "unknown"
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=repo_root,
        )
        source = out.stdout.strip()
        result["source_commit"] = source[:12]
    except Exception:  # noqa: BLE001
        result["source_commit"] = "unknown"

    try:
        out = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=repo_root,
        )
        remote = out.stdout.strip()
        result["remote_commit"] = remote[:12]
        result["is_drifted"] = bool(source and remote and source != remote)
        if result["is_drifted"]:
            result["drift_details"] = "deployed version differs from origin/main"
        else:
            result["drift_details"] = "up to date"
    except Exception:  # noqa: BLE001
        result["is_drifted"] = False
        result["remote_commit"] = "unknown"
        result["drift_details"] = "could not reach origin/main"

    result["process_pid"] = os.getpid()
    return result


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.get("/api/deployment/git-drift")
async def get_git_drift() -> dict:
    """Return git-commit-based drift: compares HEAD against origin/main."""
    return await _fetch_git_drift()


@router.get("/api/diagnostics/summary")
async def get_diagnostics_summary() -> dict:
    """Consolidated diagnostics for the Diagnostics tab."""
    summary: dict[str, object] = {}

    # WSL status
    try:
        wsl_result = subprocess.run(
            ["wsl", "-l", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-16-le",
            errors="replace",
        )
        summary["wsl_status"] = wsl_result.stdout.strip()
        summary["wsl_available"] = wsl_result.returncode == 0
    except Exception:  # noqa: BLE001
        try:
            wsl_result_raw = subprocess.run(
                ["wsl", "-l", "-v"],
                capture_output=True,
                timeout=10,
            )
            summary["wsl_status"] = wsl_result_raw.stdout.decode("utf-16-le", errors="replace").strip()
            summary["wsl_available"] = wsl_result_raw.returncode == 0
        except Exception:  # noqa: BLE001
            summary["wsl_status"] = "WSL not available"
            summary["wsl_available"] = False

    # Dashboard process info
    proc = psutil.Process(os.getpid())
    summary["dashboard_pid"] = proc.pid
    summary["dashboard_memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
    summary["dashboard_port"] = _PORT

    # Git commit
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=_REPO_ROOT or Path(__file__).parent.parent,
        )
        summary["git_commit"] = out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        summary["git_commit"] = "unknown"

    # Drift info
    try:
        drift = await _fetch_git_drift()
        summary["is_drifted"] = drift.get("is_drifted", False)
        summary["source_commit"] = drift.get("source_commit", "unknown")
        summary["remote_commit"] = drift.get("remote_commit", "unknown")
        summary["drift_details"] = drift.get("drift_details", "")
    except Exception:  # noqa: BLE001
        summary["is_drifted"] = False

    return summary


@router.post("/api/diagnostics/restart-service")
async def restart_dashboard_service(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("system.control")),
) -> dict:
    """Restart the dashboard systemd service (WSL/Linux only, localhost only)."""
    client = request.client
    if not client or client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="Local access only")

    try:
        result = subprocess.run(
            [_SYSTEMCTL_BIN, "--user", "restart", "runner-dashboard"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "success": result.returncode == 0,
            "output": (result.stdout + result.stderr).strip(),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to restart runner-dashboard service")
        raise HTTPException(status_code=500, detail="Restart failed") from exc


@router.post("/api/launchers/generate")
async def generate_launchers(
    request: Request,
    principal: Principal = Depends(require_scope("system.control")),
) -> dict:
    """Generate Windows PowerShell launcher scripts on the Desktop."""
    output_dir = Path.home() / "Desktop" / "RunnerDashboard"
    output_dir.mkdir(parents=True, exist_ok=True)

    launchers_created: list[str] = []

    script = output_dir / "Open-Dashboard.ps1"
    script.write_text('Start-Process "http://localhost:8321"\n', encoding="utf-8")
    launchers_created.append(str(script))

    keepalive = output_dir / "Start-WSL-Keepalive.ps1"
    keepalive.write_text(
        'Start-ScheduledTask -TaskName "WSL-Dashboard-Keepalive" -ErrorAction SilentlyContinue\n'
        'Write-Host "Keepalive task started"\n',
        encoding="utf-8",
    )
    launchers_created.append(str(keepalive))

    restart = output_dir / "Restart-Dashboard-Service.ps1"
    restart.write_text(
        'wsl -e bash -c "systemctl --user restart runner-dashboard && echo Service restarted"\n',
        encoding="utf-8",
    )
    launchers_created.append(str(restart))

    diag = output_dir / "Open-Diagnostics.ps1"
    diag.write_text('Start-Process "http://localhost:8321/#diagnostics"\n', encoding="utf-8")
    launchers_created.append(str(diag))

    log.info("Generated %d launcher scripts in %s", len(launchers_created), output_dir)
    return {
        "output_dir": str(output_dir),
        "launchers": launchers_created,
        "message": f"Created {len(launchers_created)} launcher scripts in {output_dir}",
    }


# ─── Runner Routing Audit ─────────────────────────────────────────────────────


@router.get("/api/runner-routing-audit")
async def get_runner_routing_audit() -> JSONResponse:
    """Return recent workflow runs that executed on GitHub-hosted runners."""
    return JSONResponse(_runner_audit_cache)


@router.post("/api/runner-routing-audit/refresh")
async def refresh_runner_routing_audit() -> JSONResponse:
    """Trigger an immediate audit refresh."""
    asyncio.create_task(_run_runner_audit())
    return JSONResponse({"status": "refresh triggered"})


async def _run_runner_audit() -> None:
    async with _runner_audit_lock:
        try:
            violations = await _fetch_hosted_runner_violations()
            _runner_audit_cache["violations"] = violations
            _runner_audit_cache["last_checked"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            _runner_audit_cache["error"] = None
            if violations:
                log.warning(
                    "BILLING ALERT: %d workflow run(s) detected on GitHub-hosted runners",
                    len(violations),
                )
        except Exception as exc:  # noqa: BLE001
            _runner_audit_cache["error"] = str(exc)
            log.error("Runner routing audit failed: %s", exc)


async def _fetch_hosted_runner_violations() -> list[dict[str, Any]]:
    """Query GitHub API for recent runs on hosted runners across org repos."""
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    org = _ORG
    violations: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30) as client:
        repos_resp = await client.get(
            f"https://api.github.com/orgs/{org}/repos",
            headers=headers,
            params={"per_page": 50, "sort": "pushed"},
        )
        if repos_resp.status_code != 200:
            return []
        repos = [r["name"] for r in repos_resp.json()]

        for repo_name in repos[:20]:  # limit to 20 most recently pushed
            try:
                runs_resp = await client.get(
                    f"https://api.github.com/repos/{org}/{repo_name}/actions/runs",
                    headers=headers,
                    params={"per_page": 10, "status": "completed"},
                )
                if runs_resp.status_code != 200:
                    continue
                for run in runs_resp.json().get("workflow_runs", []):
                    jobs_resp = await client.get(
                        f"https://api.github.com/repos/{org}/{repo_name}/actions/runs/{run['id']}/jobs",
                        headers=headers,
                        params={"per_page": 30},
                    )
                    if jobs_resp.status_code != 200:
                        continue
                    for job in jobs_resp.json().get("jobs", []):
                        runner_name = job.get("runner_name") or ""
                        runner_group = job.get("runner_group_name") or ""
                        if HOSTED_RUNNER_PATTERNS.match(runner_name) or runner_group == "GitHub Actions":
                            violations.append(
                                {
                                    "repo": repo_name,
                                    "workflow": run.get("name", ""),
                                    "run_id": run["id"],
                                    "job_name": job.get("name", ""),
                                    "runner_name": runner_name,
                                    "runner_group": runner_group,
                                    "run_url": run.get("html_url", ""),
                                    "started_at": job.get("started_at", ""),
                                    "conclusion": job.get("conclusion", ""),
                                }
                            )
            except Exception:  # noqa: BLE001
                continue

    return violations


async def runner_audit_loop() -> None:
    """Background task: poll GitHub every 15 minutes for billing violations."""
    await asyncio.sleep(30)  # initial delay
    while True:
        await _run_runner_audit()
        await asyncio.sleep(900)  # 15 minutes

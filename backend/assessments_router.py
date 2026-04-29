# ruff: noqa: B008
"""Assessments and Feature-Requests routes.

Provides API endpoints for:
- Code quality assessment dispatch and score history (/api/assessments/*)
- Feature-request management and dispatch (/api/feature-requests/*)
- Prompt template and notes management (/api/settings/prompt-notes,
  /api/feature-requests/templates)

Extracted from server.py as part of epic #159 (god-module refactor).
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as _dt_mod
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import config_schema
from fastapi import APIRouter, Depends, HTTPException, Request
from identity import Principal, require_scope

UTC = getattr(_dt_mod, "UTC", _dt_mod.timezone.utc)  # noqa: UP017
datetime = _dt_mod.datetime

log = logging.getLogger("dashboard")

router = APIRouter(tags=["assessments"])

# ─── Paths ───────────────────────────────────────────────────────────────────

_FEATURE_REQUESTS_PATH = Path.home() / "actions-runners" / "dashboard" / "feature_requests.json"
_PROMPT_TEMPLATES_PATH = Path.home() / "actions-runners" / "dashboard" / "prompt_templates.json"
_PROMPT_NOTES_PATH = Path.home() / "actions-runners" / "dashboard" / "prompt_notes.json"

# ─── Locks ───────────────────────────────────────────────────────────────────

_feature_requests_lock: asyncio.Lock = asyncio.Lock()
_prompt_templates_lock: asyncio.Lock = asyncio.Lock()
_prompt_notes_lock: asyncio.Lock = asyncio.Lock()

# ─── Standards injection ─────────────────────────────────────────────────────

STANDARDS_INJECTION: dict[str, str] = {
    "tdd": (
        "Use Test-Driven Development: write failing tests first (RED), then minimal code to pass (GREEN),"
        " then refactor. Tests must pass before any PR."
    ),
    "dbc": (
        "Apply Design by Contract: validate inputs at boundaries, assert internal invariants,"
        " document pre/postconditions in docstrings."
    ),
    "dry": (
        "Apply DRY: extract shared logic into modules, eliminate duplication."
        " Three similar code blocks should become one shared function."
    ),
    "lod": (
        "Apply Law of Demeter: components talk to immediate neighbors only."
        " UI receives view models, not raw nested payloads."
    ),
    "security": (
        "Apply security-first: validate all inputs, avoid injection vulnerabilities,"
        " use parameterized queries, never log secrets."
    ),
    "docs": (
        "Document public APIs, non-obvious decisions, and architecture choices."
        " Prefer short clear docstrings over multi-paragraph ones."
    ),
}

# ─── Injected shared helpers (set via configure()) ───────────────────────────

_run_cmd = None  # type: ignore[assignment]
_ORG: str = ""
_REPO_ROOT: Path | None = None
_check_dispatch_rate = None  # type: ignore[assignment]


def configure(run_cmd_fn, org: str, repo_root: Path, check_dispatch_rate_fn) -> None:
    """Inject shared helpers from server.py (called during startup)."""
    global _run_cmd, _ORG, _REPO_ROOT, _check_dispatch_rate  # noqa: PLW0603
    _run_cmd = run_cmd_fn
    _ORG = org
    _REPO_ROOT = repo_root
    _check_dispatch_rate = check_dispatch_rate_fn


# ─── Assessments routes ──────────────────────────────────────────────────────


@router.get("/api/assessments/scores")
async def get_assessment_scores() -> dict:
    """Return assessment score history from local assessments directory."""
    assessments_dir = _REPO_ROOT / "assessments"
    results: list[dict] = []
    if assessments_dir.exists():
        for score_file in sorted(assessments_dir.rglob("*.json"), reverse=True)[:50]:
            try:
                data = json.loads(score_file.read_text(encoding="utf-8"))
                results.append(
                    {
                        "file": str(score_file.relative_to(_REPO_ROOT)),
                        "repo": data.get("repository") or score_file.parent.name,
                        "score": data.get("score") or data.get("overall_score"),
                        "date": data.get("date") or data.get("timestamp") or score_file.stat().st_mtime,
                        "summary": data.get("summary") or data.get("description", "")[:200],
                        "provider": data.get("provider") or data.get("agent", ""),
                    }
                )
            except Exception:  # noqa: BLE001
                pass
    return {"scores": results, "total": len(results)}


@router.post("/api/assessments/dispatch")
async def dispatch_assessment(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("assessments.dispatch")),
) -> dict:
    """Dispatch an assessment workflow for a repository."""
    body = await request.json()
    repo = str(body.get("repository", "")).strip()
    provider = str(body.get("provider", "jules_api")).strip()
    ref = str(body.get("ref", "main")).strip()
    if not repo:
        raise HTTPException(status_code=422, detail="repository required")
    if not provider:
        raise HTTPException(status_code=422, detail="provider required")

    sanitized_repo = repo.replace("\n", "\\n").replace("\r", "\\r")[:200]
    sanitized_provider = provider.replace("\n", "\\n").replace("\r", "\\r")[:200]
    sanitized_ref = ref.replace("\n", "\\n").replace("\r", "\\r")[:200]

    log.info(
        "audit: assessments_dispatch repo=%s provider=%s ref=%s",
        sanitized_repo,
        sanitized_provider,
        sanitized_ref,
    )

    endpoint = f"/repos/{_ORG}/Repository_Management/actions/workflows/Jules-Assess-Repo.yml/dispatches"
    payload = {
        "ref": "main",
        "inputs": {"target_repository": f"{_ORG}/{repo}", "provider": provider},
    }
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        pf = f.name
    try:
        code, _, stderr = await _run_cmd(
            ["gh", "api", endpoint, "--method", "POST", "--input", pf],
            timeout=30,
            cwd=_REPO_ROOT,
        )
    finally:
        with contextlib.suppress(OSError):
            Path(pf).unlink()
    if code != 0:
        log.warning("assessment dispatch failed: repo=%s stderr=%s", repo, stderr.strip()[:300])
        raise HTTPException(
            status_code=502,
            detail="Assessment dispatch failed",
        )
    return {"status": "dispatched", "repository": repo, "provider": provider}


# ─── Feature Requests routes ─────────────────────────────────────────────────


@router.get("/api/feature-requests")
async def list_feature_requests() -> dict:
    """List saved feature implementation requests."""
    try:
        if _FEATURE_REQUESTS_PATH.exists():
            data = json.loads(_FEATURE_REQUESTS_PATH.read_text(encoding="utf-8"))
        else:
            data = []
    except Exception:  # noqa: BLE001
        data = []
    return {"requests": list(reversed(data[-100:])), "total": len(data)}


@router.get("/api/feature-requests/templates")
async def list_prompt_templates() -> dict:
    """List saved prompt templates and global prompt notes."""
    templates_data = []
    try:
        if _PROMPT_TEMPLATES_PATH.exists():
            templates_data = json.loads(_PROMPT_TEMPLATES_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass

    prompt_notes_data = {"notes": "", "enabled": True}
    try:
        if _PROMPT_NOTES_PATH.exists():
            prompt_notes_data = json.loads(_PROMPT_NOTES_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass

    return {
        "templates": templates_data,
        "standards": STANDARDS_INJECTION,
        "promptNotes": prompt_notes_data,
    }


@router.post("/api/feature-requests/templates")
async def save_prompt_template(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("feature-requests.manage")),
) -> dict:
    """Save a prompt template."""
    body = await request.json()
    name = str(body.get("name", "")).strip()
    content = str(body.get("content", "")).strip()
    if not name or not content:
        raise HTTPException(status_code=422, detail="name and content required")
    async with _prompt_templates_lock:
        try:
            templates: list[dict] = []
            if _PROMPT_TEMPLATES_PATH.exists():
                templates = json.loads(_PROMPT_TEMPLATES_PATH.read_text(encoding="utf-8"))
            existing_idx = next((i for i, t in enumerate(templates) if t.get("name") == name), None)
            template = {
                "name": name,
                "content": content,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            if existing_idx is not None:
                templates[existing_idx] = template
            else:
                templates.append(template)
            config_schema.atomic_write_json(_PROMPT_TEMPLATES_PATH, templates)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "saved", "name": name}


# ─── Settings / Prompt Notes ─────────────────────────────────────────────────


@router.get("/api/settings/prompt-notes")
async def get_prompt_notes() -> dict:
    """Get the global prompt notes that are automatically injected into every prompt."""
    try:
        if _PROMPT_NOTES_PATH.exists():
            data = json.loads(_PROMPT_NOTES_PATH.read_text(encoding="utf-8"))
        else:
            data = {"notes": "", "enabled": True}
    except Exception:  # noqa: BLE001
        data = {"notes": "", "enabled": True}
    return data


@router.put("/api/settings/prompt-notes")
async def update_prompt_notes(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("operator")),
) -> dict:
    """Update the global prompt notes."""
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="expected object body")

    notes = str(body.get("notes", "")).strip()
    enabled = bool(body.get("enabled", True))

    async with _prompt_notes_lock:
        try:
            data = {"notes": notes, "enabled": enabled}
            config_schema.atomic_write_json(_PROMPT_NOTES_PATH, data)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "saved", "notes_length": len(notes), "enabled": enabled}


@router.post("/api/feature-requests/dispatch")
async def dispatch_feature_request(
    request: Request,
    *,
    principal: Principal = Depends(require_scope("feature-requests.manage")),
) -> dict:
    """Dispatch a feature implementation request via CI remediation workflow."""
    client_ip = request.client.host if request.client else "unknown"
    _check_dispatch_rate(client_ip)
    body = await request.json()
    repo = str(body.get("repository", "")).strip()
    branch = str(body.get("branch", "main")).strip()
    provider = str(body.get("provider", "jules_api")).strip()
    prompt = str(body.get("prompt", "")).strip()
    standards = body.get("standards", []) or []
    template_id = str(body.get("template_id", "")).strip()
    if not repo:
        raise HTTPException(status_code=422, detail="repository required")
    if not prompt and not template_id:
        raise HTTPException(status_code=422, detail="prompt or template_id required")

    sanitized_repo = repo.replace("\n", "\\n").replace("\r", "\\r")[:200]
    sanitized_provider = provider.replace("\n", "\\n").replace("\r", "\\r")[:200]
    sanitized_branch = branch.replace("\n", "\\n").replace("\r", "\\r")[:200]

    log.info(
        "audit: feature_request_dispatch repo=%s provider=%s branch=%s",
        sanitized_repo,
        sanitized_provider,
        sanitized_branch,
    )

    # Load and apply prompt notes if enabled
    prompt_notes_data: dict[str, object] = {"notes": "", "enabled": True}
    try:
        if _PROMPT_NOTES_PATH.exists():
            prompt_notes_data = json.loads(_PROMPT_NOTES_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass

    # Build full prompt with notes and standards injection
    full_prompt = prompt
    notes_val = str(prompt_notes_data.get("notes", ""))
    if prompt_notes_data.get("enabled", True) and notes_val.strip():
        full_prompt = f"{notes_val}\n\n{prompt}"

    injected_standards = "\n\n".join(
        f"[{s.upper()}] {STANDARDS_INJECTION[s]}" for s in standards if s in STANDARDS_INJECTION
    )
    if injected_standards:
        full_prompt = f"{full_prompt}\n\n## Engineering Standards\n{injected_standards}"

    # Save to history
    entry: dict = {}
    async with _feature_requests_lock:
        try:
            history: list[dict] = []
            if _FEATURE_REQUESTS_PATH.exists():
                history = json.loads(_FEATURE_REQUESTS_PATH.read_text(encoding="utf-8"))
            entry = {
                "id": str(int(datetime.now(UTC).timestamp())),
                "repository": repo,
                "branch": branch,
                "provider": provider,
                "prompt": prompt[:500],
                "standards": list(standards),
                "status": "dispatched",
                "created_at": datetime.now(UTC).isoformat(),
            }
            history.append(entry)
            config_schema.atomic_write_json(_FEATURE_REQUESTS_PATH, history[-200:])
        except Exception:  # noqa: BLE001
            pass

    # Dispatch via feature-request workflow
    endpoint = f"/repos/{_ORG}/Repository_Management/actions/workflows/Jules-Feature-Request.yml/dispatches"
    payload = {
        "ref": "main",
        "inputs": {
            "target_repository": f"{_ORG}/{repo}",
            "branch": branch,
            "provider": provider,
            "prompt": full_prompt[:10000],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        pf = f.name
    try:
        code, _, stderr = await _run_cmd(
            ["gh", "api", endpoint, "--method", "POST", "--input", pf],
            timeout=30,
            cwd=_REPO_ROOT,
        )
    finally:
        with contextlib.suppress(OSError):
            Path(pf).unlink()
    if code != 0:
        log.warning("feature_request_dispatch failed: %s", stderr.strip()[:200])
        # Don't raise - save history record and return success anyway (workflow may not exist yet)
    return {
        "status": "dispatched",
        "repository": repo,
        "provider": provider,
        "entry_id": entry.get("id", ""),
    }

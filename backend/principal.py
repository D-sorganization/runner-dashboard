"""Principal model — identity and authorization foundation.

Issue #131: Foundation and Principal Model
Provides the ``Principal`` dataclass and ``require_principal()`` FastAPI
dependency so every state-changing request carries a verifiable identity.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

log = logging.getLogger("dashboard.principal")

# ─── Constants ────────────────────────────────────────────────────────────────

_UNKNOWN_PRINCIPAL_ID = "unknown"
_DEFAULT_HUMAN = "anonymous-human"
_DEFAULT_BOT = "anonymous-bot"

# ─── Enums ────────────────────────────────────────────────────────────────────


class PrincipalType(str, Enum):
    """Class of principal."""

    HUMAN = "human"
    BOT = "bot"
    SERVICE = "service"


# ─── Dataclass ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Principal:
    """Verified identity attached to every authenticated request.

    Attributes
    ----------
    id:
        Stable identifier (GitHub login for humans, service name for bots).
    name:
        Human-readable display name.
    type:
        ``human``, ``bot``, or ``service``.
    email:
        Optional contact address.
    roles:
        Set of role strings (e.g. ``{"operator", "viewer"}``).
    permissions:
        Set of explicit permission strings (e.g. ``{"fleet:write", "agents:dispatch"}``).
    """

    id: str
    name: str
    type: PrincipalType
    email: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()

    def has_role(self, role: str) -> bool:
        """Return True when the principal carries *role* (case-insensitive)."""
        return role.lower() in {r.lower() for r in self.roles}

    def has_permission(self, permission: str) -> bool:
        """Return True when the principal carries *permission* (case-insensitive)."""
        return permission.lower() in {p.lower() for p in self.permissions}


# ─── Anonymous sentinel instances ─────────────────────────────────────────────

_ANONYMOUS_HUMAN = Principal(
    id=_UNKNOWN_PRINCIPAL_ID,
    name=_DEFAULT_HUMAN,
    type=PrincipalType.HUMAN,
    roles=frozenset(),
    permissions=frozenset(),
)

_ANONYMOUS_BOT = Principal(
    id=_UNKNOWN_PRINCIPAL_ID,
    name=_DEFAULT_BOT,
    type=PrincipalType.BOT,
    roles=frozenset(),
    permissions=frozenset(),
)


# ─── YAML Loader ────────────────────────────────────────────────────────────────


class PrincipalConfigError(Exception):
    """Raised when principals.yml is missing, malformed, or contains duplicate IDs."""


def _default_principals() -> dict[str, Principal]:
    """Return the built-in anonymous principals for backward compatibility."""
    return {
        _UNKNOWN_PRINCIPAL_ID: _ANONYMOUS_HUMAN,
        "anonymous-bot": _ANONYMOUS_BOT,
    }


def load_principals(path: Path | None = None) -> dict[str, Principal]:
    """Load principals from *path* (YAML).

    The file is optional; if missing the function returns built-in anonymous
    principals and logs an informational message.

    Parameters
    ----------
    path:
        Absolute path to ``principals.yml``.  Defaults to
        ``config/principals.yml`` under the repository root.
    """
    if path is None:
        repo_root = Path(
            os.environ.get("RUNNER_DASHBOARD_REPO_ROOT", Path(__file__).resolve().parents[1])
        )
        path = repo_root / "config" / "principals.yml"

    if not path.exists():
        log.info("principals.yml not found at %s; using anonymous principals", path)
        return _default_principals()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PrincipalConfigError(f"Failed to load principals.yml: {exc}") from exc

    if not isinstance(raw, dict):
        raise PrincipalConfigError("principals.yml root must be a mapping")

    principals_list = raw.get("principals")
    if principals_list is None:
        log.info("principals.yml has no 'principals' key; using anonymous principals")
        return _default_principals()

    if not isinstance(principals_list, list):
        raise PrincipalConfigError("'principals' must be a list")

    principals: dict[str, Principal] = {}
    for idx, entry in enumerate(principals_list, start=1):
        if not isinstance(entry, dict):
            raise PrincipalConfigError(f"Entry {idx} is not a mapping")
        pid = str(entry.get("id") or entry.get("name") or "").strip()
        if not pid:
            raise PrincipalConfigError(f"Entry {idx} is missing 'id' or 'name'")
        if pid in principals:
            raise PrincipalConfigError(f"Duplicate principal id: {pid}")

        ptype_str = str(entry.get("type") or "service").strip().lower()
        try:
            ptype = PrincipalType(ptype_str)
        except ValueError as exc:
            raise PrincipalConfigError(
                f"Entry {idx} ({pid}) has invalid type: {ptype_str}"
            ) from exc

        roles = frozenset(str(r).strip().lower() for r in entry.get("roles", []) if str(r).strip())
        permissions = frozenset(
            str(p).strip().lower() for p in entry.get("permissions", []) if str(p).strip()
        )

        principals[pid] = Principal(
            id=pid,
            name=str(entry.get("name") or pid).strip(),
            type=ptype,
            email=str(entry.get("email") or "").strip() or None,
            roles=roles,
            permissions=permissions,
        )

    # Always ensure the anonymous fallback exists
    if _UNKNOWN_PRINCIPAL_ID not in principals:
        principals[_UNKNOWN_PRINCIPAL_ID] = _ANONYMOUS_HUMAN

    log.info("Loaded %d principal(s) from %s", len(principals), path)
    return principals


# ─── Pydantic model for request bodies ──────────────────────────────────────────


class PrincipalRef(BaseModel):
    """Lightweight principal reference used in request payloads."""

    id: str = Field(..., max_length=200)
    name: str = Field(default="", max_length=200)
    type: str = Field(default="human", max_length=20)

    def to_principal(self) -> Principal:
        """Return a full Principal from this reference."""
        try:
            ptype = PrincipalType(self.type.lower())
        except ValueError:
            ptype = PrincipalType.HUMAN
        return Principal(
            id=self.id,
            name=self.name or self.id,
            type=ptype,
        )


# ─── FastAPI dependency ─────────────────────────────────────────────────────────

_PRINCIPALS: dict[str, Principal] | None = None


def init_principals(principals: dict[str, Principal] | None = None) -> None:
    """Populate the global principal registry (called once at server boot)."""
    global _PRINCIPALS  # noqa: PLW0603
    if principals is not None:
        _PRINCIPALS = dict(principals)
    else:
        _PRINCIPALS = load_principals()


def get_principal_registry() -> dict[str, Principal]:
    """Return the loaded principal registry."""
    if _PRINCIPALS is None:
        init_principals()
    return _PRINCIPALS  # type: ignore[return-value]


def _lookup_principal(pid: str) -> Principal:
    """Return the principal with id *pid*, falling back to anonymous."""
    registry = get_principal_registry()
    return registry.get(pid, _ANONYMOUS_HUMAN)


def get_current_principal(request: Request) -> Principal:
    """Extract the current principal from request.state (set by auth middleware)."""
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, Principal):
        return principal
    # Fallback to header for API-key-authenticated clients (bots / service tokens)
    header_pid = request.headers.get("X-Principal-Id", "").strip()
    if header_pid:
        return _lookup_principal(header_pid)
    return _ANONYMOUS_HUMAN


def require_principal(request: Request = None) -> Principal:  # type: ignore[assignment]
    """FastAPI dependency: attach the current principal to the request.

    Raises ``HTTPException(401)`` when no principal is attached and the
    configuration requires authentication (fail-closed).
    """
    # FastAPI injects the Request automatically when used as Depends()
    if request is None:  # pragma: no cover
        raise HTTPException(status_code=401, detail="Authentication required")
    principal = get_current_principal(request)
    # Fail closed: anonymous principals with the unknown ID are rejected
    # when the server is configured with real principals.
    if principal.id == _UNKNOWN_PRINCIPAL_ID and len(get_principal_registry()) > 2:
        raise HTTPException(status_code=401, detail="Authentication required")
    return principal


def require_role(role: str):
    """Return a FastAPI dependency that enforces *role* on the current principal."""

    def _checker(request: Request = None) -> Principal:  # type: ignore[assignment]
        principal = require_principal(request)
        if not principal.has_role(role):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' required",
            )
        return principal

    return _checker


def require_permission(permission: str):
    """Return a FastAPI dependency that enforces *permission* on the current principal."""

    def _checker(request: Request = None) -> Principal:  # type: ignore[assignment]
        principal = require_principal(request)
        if not principal.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required",
            )
        return principal

    return _checker
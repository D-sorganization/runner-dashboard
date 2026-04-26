"""Tests for the principal identity and authorization module (issue #131)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import principal as principal_mod  # noqa: E402
from principal import (  # noqa: E402
    Principal,
    PrincipalConfigError,
    PrincipalRef,
    PrincipalType,
    get_current_principal,
    get_principal_registry,
    init_principals,
    load_principals,
    require_permission,
    require_principal,
    require_role,
)


@pytest.fixture(autouse=True)
def _reset_principals():
    """Reset the global principal registry before every test."""
    principal_mod._PRINCIPALS = None
    yield
    principal_mod._PRINCIPALS = None


# ─── Principal dataclass ────────────────────────────────────────────────────────


class TestPrincipalDataclass:
    def test_principal_equality(self) -> None:
        p1 = Principal(id="alice", name="Alice", type=PrincipalType.HUMAN, roles=frozenset({"operator"}))
        p2 = Principal(id="alice", name="Alice", type=PrincipalType.HUMAN, roles=frozenset({"operator"}))
        assert p1 == p2

    def test_has_role_case_insensitive(self) -> None:
        p = Principal(id="alice", name="Alice", type=PrincipalType.HUMAN, roles=frozenset({"Operator"}))
        assert p.has_role("operator")
        assert p.has_role("OPERATOR")

    def test_has_role_missing(self) -> None:
        p = Principal(id="alice", name="Alice", type=PrincipalType.HUMAN)
        assert not p.has_role("admin")

    def test_has_permission_case_insensitive(self) -> None:
        p = Principal(
            id="alice",
            name="Alice",
            type=PrincipalType.HUMAN,
            permissions=frozenset({"Fleet:Write"}),
        )
        assert p.has_permission("fleet:write")
        assert p.has_permission("FLEET:WRITE")

    def test_frozen_dataclass_cannot_mutate(self) -> None:
        p = Principal(id="alice", name="Alice", type=PrincipalType.HUMAN)
        with pytest.raises(AttributeError):
            p.name = "Bob"  # type: ignore[misc]


# ─── PrincipalType enum ─────────────────────────────────────────────────────────


class TestPrincipalType:
    def test_from_string_valid(self) -> None:
        assert PrincipalType("human") == PrincipalType.HUMAN
        assert PrincipalType("bot") == PrincipalType.BOT
        assert PrincipalType("service") == PrincipalType.SERVICE

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            PrincipalType("alien")


# ─── YAML loader ────────────────────────────────────────────────────────────────


class TestLoadPrincipals:
    def test_missing_file_returns_anonymous(self, tmp_path: Path) -> None:
        result = load_principals(tmp_path / "nonexistent.yml")
        assert "unknown" in result
        assert result["unknown"].type == PrincipalType.HUMAN

    def test_empty_principals_key_returns_anonymous(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        path.write_text("principals:\n")
        result = load_principals(path)
        assert "unknown" in result

    def test_loads_single_principal(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {
            "principals": [
                {
                    "id": "alice",
                    "name": "Alice",
                    "type": "human",
                    "email": "alice@example.com",
                    "roles": ["operator", "viewer"],
                    "permissions": ["fleet:read", "fleet:write"],
                }
            ]
        }
        path.write_text(yaml.dump(data))
        result = load_principals(path)
        assert "alice" in result
        alice = result["alice"]
        assert alice.name == "Alice"
        assert alice.email == "alice@example.com"
        assert alice.type == PrincipalType.HUMAN
        assert alice.has_role("operator")
        assert alice.has_role("viewer")
        assert alice.has_permission("fleet:read")

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {"principals": [{"id": "alice"}, {"id": "alice"}]}
        path.write_text(yaml.dump(data))
        with pytest.raises(PrincipalConfigError, match="Duplicate principal id"):
            load_principals(path)

    def test_invalid_type_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {"principals": [{"id": "alice", "type": "alien"}]}
        path.write_text(yaml.dump(data))
        with pytest.raises(PrincipalConfigError, match="invalid type"):
            load_principals(path)

    def test_missing_id_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {"principals": [{"name": ""}]}
        path.write_text(yaml.dump(data))
        with pytest.raises(PrincipalConfigError, match="missing"):
            load_principals(path)

    def test_root_not_dict_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        path.write_text("- not a dict")
        with pytest.raises(PrincipalConfigError, match="root must be a mapping"):
            load_principals(path)

    def test_principals_not_list_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {"principals": "notalist"}
        path.write_text(yaml.dump(data))
        with pytest.raises(PrincipalConfigError, match="'principals' must be a list"):
            load_principals(path)

    def test_ensures_unknown_fallback(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {"principals": [{"id": "alice", "name": "Alice"}]}
        path.write_text(yaml.dump(data))
        result = load_principals(path)
        assert "unknown" in result
        assert result["unknown"].id == "unknown"

    def test_roles_permissions_normalised_to_lower(self, tmp_path: Path) -> None:
        path = tmp_path / "principals.yml"
        data = {
            "principals": [
                {
                    "id": "alice",
                    "roles": ["Operator"],
                    "permissions": ["Fleet:Write"],
                }
            ]
        }
        path.write_text(yaml.dump(data))
        result = load_principals(path)
        alice = result["alice"]
        assert alice.has_role("operator")
        assert alice.has_permission("fleet:write")


# ─── FastAPI dependency helpers ─────────────────────────────────────────────────


class FakeRequest:
    """Minimal ASGI request stand-in for testing."""

    def __init__(self, headers: dict[str, str] | None = None, state_principal: Principal | None = None) -> None:
        self.headers = headers or {}
        self.state = type("State", (), {})()
        if state_principal:
            self.state.principal = state_principal


class TestGetCurrentPrincipal:
    def test_from_request_state(self) -> None:
        p = Principal(id="alice", name="Alice", type=PrincipalType.HUMAN)
        req = FakeRequest(state_principal=p)
        assert get_current_principal(req) == p  # type: ignore[arg-type]

    def test_from_header(self) -> None:
        init_principals(
            {
                "alice": Principal(id="alice", name="Alice", type=PrincipalType.HUMAN),
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
            }
        )
        req = FakeRequest(headers={"X-Principal-Id": "alice"})
        result = get_current_principal(req)  # type: ignore[arg-type]
        assert result.id == "alice"

    def test_unknown_header_returns_anonymous(self) -> None:
        init_principals(
            {
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
            }
        )
        req = FakeRequest(headers={"X-Principal-Id": "nobody"})
        result = get_current_principal(req)  # type: ignore[arg-type]
        assert result.id == "unknown"

    def test_no_header_no_state_returns_anonymous(self) -> None:
        req = FakeRequest()
        result = get_current_principal(req)  # type: ignore[arg-type]
        assert result.id == "unknown"


class TestRequirePrincipal:
    def test_no_request_raises_401(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            require_principal(None)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401

    def test_anonymous_with_only_defaults_allowed(self) -> None:
        """When only anonymous principals exist, anonymous is allowed."""
        init_principals()
        req = FakeRequest()
        result = require_principal(req)  # type: ignore[arg-type]
        assert result.id == "unknown"

    def test_anonymous_with_real_principals_rejected(self) -> None:
        """Fail-closed: anonymous rejected when real principals configured."""
        from fastapi import HTTPException

        init_principals(
            {
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
                "anonymous-bot": Principal(id="anonymous-bot", name="Anonymous Bot", type=PrincipalType.BOT),
                "alice": Principal(id="alice", name="Alice", type=PrincipalType.HUMAN),
            }
        )
        req = FakeRequest()
        with pytest.raises(HTTPException) as exc_info:
            require_principal(req)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401


class TestRequireRole:
    def test_has_role_returns_principal(self) -> None:
        init_principals(
            {
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
                "alice": Principal(id="alice", name="Alice", type=PrincipalType.HUMAN, roles=frozenset({"operator"})),
            }
        )
        req = FakeRequest(headers={"X-Principal-Id": "alice"})
        dep = require_role("operator")
        result = dep(req)  # type: ignore[arg-type]
        assert result.id == "alice"

    def test_missing_role_raises_403(self) -> None:
        from fastapi import HTTPException

        init_principals(
            {
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
                "alice": Principal(id="alice", name="Alice", type=PrincipalType.HUMAN),
            }
        )
        req = FakeRequest(headers={"X-Principal-Id": "alice"})
        dep = require_role("operator")
        with pytest.raises(HTTPException) as exc_info:
            dep(req)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 403


class TestRequirePermission:
    def test_has_permission_returns_principal(self) -> None:
        init_principals(
            {
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
                "alice": Principal(
                    id="alice", name="Alice", type=PrincipalType.HUMAN, permissions=frozenset({"fleet:write"})
                ),
            }
        )
        req = FakeRequest(headers={"X-Principal-Id": "alice"})
        dep = require_permission("fleet:write")
        result = dep(req)  # type: ignore[arg-type]
        assert result.id == "alice"

    def test_missing_permission_raises_403(self) -> None:
        from fastapi import HTTPException

        init_principals(
            {
                "unknown": Principal(id="unknown", name="Unknown", type=PrincipalType.HUMAN),
                "alice": Principal(id="alice", name="Alice", type=PrincipalType.HUMAN),
            }
        )
        req = FakeRequest(headers={"X-Principal-Id": "alice"})
        dep = require_permission("fleet:write")
        with pytest.raises(HTTPException) as exc_info:
            dep(req)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 403


# ─── PrincipalRef Pydantic model ────────────────────────────────────────────────


class TestPrincipalRef:
    def test_to_principal_full(self) -> None:
        ref = PrincipalRef(id="alice", name="Alice", type="human")
        p = ref.to_principal()
        assert p.id == "alice"
        assert p.name == "Alice"
        assert p.type == PrincipalType.HUMAN

    def test_to_principal_defaults_name_to_id(self) -> None:
        ref = PrincipalRef(id="alice")
        p = ref.to_principal()
        assert p.name == "alice"

    def test_to_principal_invalid_type_fallbacks_to_human(self) -> None:
        ref = PrincipalRef(id="alice", type="alien")
        p = ref.to_principal()
        assert p.type == PrincipalType.HUMAN


# ─── get_principal_registry ─────────────────────────────────────────────────────


class TestGetPrincipalRegistry:
    def test_auto_initialises(self) -> None:
        principal_mod._PRINCIPALS = None
        registry = get_principal_registry()
        assert "unknown" in registry
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

backend_dir = str(Path(__file__).parent.parent.resolve() / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

REPO_ROOT = Path(__file__).parent.parent

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Principal factory and role-based fixtures (issue #343)
# ---------------------------------------------------------------------------


def _make_principal(role: str, principal_id: str | None = None) -> "Principal":  # noqa: F821
    """Create a Principal with the given role.

    Precondition: ``role`` must be one of ``"admin"``, ``"operator"``,
    ``"viewer"``, or ``"bot"``.
    Postcondition: returns a Principal whose ``roles`` list contains
    exactly ``[role]``.
    """
    from identity import Principal

    assert role in ("admin", "operator", "viewer", "bot"), f"Unknown role: {role}"
    pid = principal_id or f"test-{role}"
    return Principal(
        id=pid,
        type="bot" if role == "bot" else "human",
        name=f"Test {role.title()}",
        roles=[role],
    )


@pytest.fixture
def make_principal():
    """Factory fixture for creating Principals with arbitrary roles.

    Usage::

        def test_something(make_principal):
            admin = make_principal("admin")
            viewer = make_principal("viewer")
    """
    return _make_principal


@pytest.fixture
def admin_principal() -> "Principal":  # noqa: F821
    """A Principal with admin role."""
    return _make_principal("admin", "test-admin")


@pytest.fixture
def operator_principal() -> "Principal":  # noqa: F821
    """A Principal with operator role."""
    return _make_principal("operator", "test-operator")


@pytest.fixture
def viewer_principal() -> "Principal":  # noqa: F821
    """A Principal with viewer role."""
    return _make_principal("viewer", "test-viewer")


# ---------------------------------------------------------------------------
# Authenticated client fixtures (issue #343)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_auth():
    """Override ``require_principal`` to return an admin Principal.

    This fixture was previously ``autouse=True``, which bypassed auth in
    every test.  Now tests must opt in explicitly via
    ``def test_xxx(mock_auth):`` or use one of the role-specific client
    fixtures (``admin_client``, ``operator_client``, ``viewer_client``).
    """
    from identity import Principal, require_principal
    from server import app

    principal = _make_principal("admin", "test-admin")
    app.dependency_overrides[require_principal] = lambda: principal
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(mock_auth) -> TestClient:
    """TestClient authenticated as admin (all scopes)."""
    from server import app

    return TestClient(app)


@pytest.fixture
def operator_client() -> TestClient:
    """TestClient authenticated as operator (limited scopes)."""
    from identity import require_principal
    from server import app

    app.dependency_overrides[require_principal] = lambda: _make_principal(
        "operator", "test-operator"
    )
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client() -> TestClient:
    """TestClient authenticated as viewer (minimal scopes)."""
    from identity import require_principal
    from server import app

    app.dependency_overrides[require_principal] = lambda: _make_principal(
        "viewer", "test-viewer"
    )
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client() -> TestClient:
    """TestClient with no authentication overrides.

    Requests through this client will hit the real ``require_principal``
    dependency.  Without loopback or valid credentials, all protected
    endpoints should return 401.
    """
    from server import app

    # Ensure no overrides leak from previous tests
    app.dependency_overrides.clear()
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def make_authed_client():
    """Factory fixture: create a TestClient authenticated as any Principal.

    Usage::

        def test_xxx(make_authed_client, admin_principal):
            client = make_authed_client(admin_principal)
            resp = client.get("/api/queue")
            assert resp.status_code == 200
    """

    def _make(principal):
        from identity import require_principal
        from server import app

        app.dependency_overrides[require_principal] = lambda: principal
        client = TestClient(app)
        return client

    return _make
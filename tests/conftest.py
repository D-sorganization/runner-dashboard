import sys
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

REPO_ROOT = Path(__file__).parent.parent

import pytest

@pytest.fixture(autouse=True)
def mock_auth():
    from server import app
    from identity import require_principal, Principal
    
    def mock_principal():
        return Principal(id="test-admin", type="bot", name="Test Admin", roles=["admin"])
        
    app.dependency_overrides[require_principal] = mock_principal
    yield
    app.dependency_overrides.clear()

"""
Unit tests for RBAC enforcement (T8-31)
6 tests: VIEWER/BUYER/ADMIN permissions on OptimizationService.run_optimization().
Since the actual codebase has no PurchaseOrderService/SupplierService, RBAC is
tested against OptimizationService (BUYER/ADMIN required) — the only service
with require_role() enforcement in this codebase.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src.services.auth_service as auth_module
from src.services.auth_service import AuthService, PermissionDeniedError
from src.services.optimization_service import OptimizationService
from src.repositories.user_repository import UserRepository
from config.constants import ROLE_ADMIN, ROLE_BUYER, ROLE_VIEWER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_user(role: str):
    """Directly set _current_user to a stub with the given role (no DB required)."""
    from unittest.mock import MagicMock
    stub = MagicMock()
    stub.role = role
    stub.username = f"{role.lower()}_user"
    auth_module._current_user = stub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_session():
    auth_module._current_user = None
    yield
    auth_module._current_user = None


@pytest.fixture
def opt_svc(clean_database):
    """OptimizationService wired to the test DB (no real data needed — role check fires first)."""
    return OptimizationService()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRBACEnforcement:

    def test_viewer_cannot_run_optimization(self, opt_svc):
        """OptimizationService.run_optimization() with VIEWER session → PermissionDeniedError."""
        _set_user(ROLE_VIEWER)
        with pytest.raises(PermissionDeniedError):
            opt_svc.run_optimization()

    def test_unauthenticated_cannot_run_optimization(self, opt_svc):
        """run_optimization() with no session (None) → PermissionDeniedError."""
        auth_module._current_user = None
        with pytest.raises(PermissionDeniedError):
            opt_svc.run_optimization()

    def test_buyer_can_run_optimization(self, opt_svc):
        """run_optimization() with BUYER session → succeeds (no exception; returns summary dict)."""
        _set_user(ROLE_BUYER)
        result = opt_svc.run_optimization()
        assert isinstance(result, dict)
        assert "total_products" in result

    def test_admin_can_run_optimization(self, opt_svc):
        """run_optimization() with ADMIN session → succeeds."""
        _set_user(ROLE_ADMIN)
        result = opt_svc.run_optimization()
        assert isinstance(result, dict)

    def test_require_role_raises_for_wrong_role(self):
        """AuthService.require_role(ROLE_ADMIN) with BUYER user raises PermissionDeniedError."""
        _set_user(ROLE_BUYER)
        with pytest.raises(PermissionDeniedError):
            AuthService.require_role(ROLE_ADMIN)

    def test_admin_has_full_require_role_access(self):
        """AuthService.require_role(ADMIN, BUYER, VIEWER) all succeed for ADMIN user."""
        _set_user(ROLE_ADMIN)
        # Should not raise for any role group that includes ADMIN
        AuthService.require_role(ROLE_ADMIN)
        AuthService.require_role(ROLE_ADMIN, ROLE_BUYER)
        AuthService.require_role(ROLE_ADMIN, ROLE_BUYER, ROLE_VIEWER)

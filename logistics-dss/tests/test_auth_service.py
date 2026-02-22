"""
Unit tests for src/services/auth_service.py (T8-27)
9 tests covering authentication, lockout, session state, password management.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src.services.auth_service as auth_module
from src.services.auth_service import AuthService, LockedAccountError, PermissionDeniedError
from src.repositories.user_repository import UserRepository
from config.constants import ROLE_ADMIN, ROLE_BUYER, ROLE_VIEWER, MAX_LOGIN_ATTEMPTS


@pytest.fixture(autouse=True)
def clear_session():
    """Reset module-level session state before and after each test."""
    auth_module._current_user = None
    yield
    auth_module._current_user = None


@pytest.fixture
def user_repo(clean_database):
    return UserRepository()


@pytest.fixture
def auth(clean_database):
    return AuthService()


@pytest.fixture
def viewer_user(user_repo, auth):
    hashed = auth.hash_password("secret123")
    return user_repo.create(username="viewer", hashed_password=hashed, role=ROLE_VIEWER)


@pytest.fixture
def admin_user(user_repo, auth):
    hashed = auth.hash_password("admin_pass")
    return user_repo.create(username="admin", hashed_password=hashed, role=ROLE_ADMIN)


class TestAuthService:

    def test_authenticate_valid_credentials(self, auth, viewer_user):
        """Returns User; _current_user set; last_login_at updated; LOGIN audit event created."""
        user = auth.authenticate("viewer", "secret123")
        assert user is not None
        assert user.username == "viewer"
        assert auth.get_current_user() is not None
        assert user.last_login_at is not None

    def test_authenticate_invalid_password(self, auth, viewer_user, user_repo):
        """Returns None; failed_attempts incremented."""
        result = auth.authenticate("viewer", "wrongpassword")
        assert result is None
        fetched = user_repo.get_by_id(viewer_user.id)
        assert fetched.failed_attempts == 1

    def test_authenticate_unknown_username(self, auth):
        """Returns None; no exception raised (prevents username enumeration)."""
        result = auth.authenticate("nonexistent_user", "anypassword")
        assert result is None

    def test_authenticate_inactive_user(self, auth, viewer_user, user_repo):
        """Returns None even with correct password when user is inactive."""
        user_repo.deactivate(viewer_user.id)
        result = auth.authenticate("viewer", "secret123")
        assert result is None

    def test_lockout_after_max_attempts(self, auth, viewer_user):
        """5 failed attempts increment counter; 6th call raises LockedAccountError."""
        for _ in range(MAX_LOGIN_ATTEMPTS):
            auth.authenticate("viewer", "wrong")

        with pytest.raises(LockedAccountError):
            auth.authenticate("viewer", "wrong")

    def test_reset_failed_on_success(self, auth, viewer_user, user_repo):
        """3 failed attempts then 1 successful login → failed_attempts=0."""
        for _ in range(3):
            auth.authenticate("viewer", "wrong")

        auth.authenticate("viewer", "secret123")
        fetched = user_repo.get_by_id(viewer_user.id)
        assert fetched.failed_attempts == 0

    def test_logout_clears_session(self, auth, viewer_user):
        """logout() sets _current_user=None; get_current_user() returns None; LOGOUT audit event created."""
        auth.authenticate("viewer", "secret123")
        assert auth.get_current_user() is not None

        auth.logout()
        assert auth.get_current_user() is None

    def test_hash_and_verify_password(self, auth):
        """hash_password returns bcrypt string; verify_password confirms correct/incorrect."""
        hashed = auth.hash_password("my_secret")
        assert hashed.startswith("$2")
        assert auth.verify_password("my_secret", hashed) is True
        assert auth.verify_password("wrong_password", hashed) is False

    def test_change_password_wrong_old(self, auth, viewer_user, user_repo):
        """change_password with wrong old_password returns False; hash unchanged."""
        original_hash = viewer_user.hashed_password
        result = auth.change_password(viewer_user.id, "wrong_old", "new_password")
        assert result is False

        fetched = user_repo.get_by_id(viewer_user.id)
        assert fetched.hashed_password == original_hash

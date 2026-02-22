"""
Authentication Service
Login, logout, session state, password hashing, lockout enforcement.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import bcrypt as _bcrypt

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.user_repository import UserRepository
from src.services.audit_service import AuditService
from src.database.models import User
from config.constants import (
    MAX_LOGIN_ATTEMPTS,
    BCRYPT_ROUNDS,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD,
    ROLE_ADMIN,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class LockedAccountError(Exception):
    """Raised when a user's account is locked due to too many failed attempts."""


class PermissionDeniedError(Exception):
    """Raised when the current user's role is not authorised for an operation."""


# ---------------------------------------------------------------------------
# Module-level session state (process-local singleton)
# ---------------------------------------------------------------------------

_current_user: Optional[User] = None

_BCRYPT_ROUNDS = BCRYPT_ROUNDS


class AuthService:
    """Authentication and session management."""

    def __init__(self):
        self._user_repo = UserRepository()
        self._audit = AuditService()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Verify credentials and open a session.

        Returns the User on success, None on invalid credentials.
        Raises LockedAccountError if the account is locked.
        """
        global _current_user

        user = self._user_repo.get_by_username(username)

        # Non-existent or inactive users → return None (no username enumeration)
        if not user or not user.active:
            return None

        # Lockout check
        if (user.failed_attempts or 0) >= MAX_LOGIN_ATTEMPTS:
            raise LockedAccountError(
                f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts."
            )

        # Password verification
        if not self.verify_password(password, user.hashed_password):
            self._user_repo.increment_failed_attempts(user.id)
            return None

        # Successful login
        self._user_repo.reset_failed_attempts(user.id)
        self._user_repo.update(user.id, last_login_at=datetime.utcnow())

        # Refresh user object to reflect updated fields
        user = self._user_repo.get_by_id(user.id)
        _current_user = user

        self._audit.log("LOGIN", actor=username)
        return user

    def logout(self) -> None:
        """Clear the session and emit a LOGOUT audit event."""
        global _current_user
        if _current_user:
            self._audit.log("LOGOUT", actor=_current_user.username)
        _current_user = None

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    @staticmethod
    def get_current_user() -> Optional[User]:
        """Return the authenticated User, or None if not logged in."""
        return _current_user

    @staticmethod
    def require_role(*roles: str) -> None:
        """Raise PermissionDeniedError if current user is not in any of roles."""
        if _current_user is None:
            raise PermissionDeniedError("Not authenticated.")
        if _current_user.role not in roles:
            raise PermissionDeniedError(
                f"Role '{_current_user.role}' is not authorised. "
                f"Required: {roles}"
            )

    # ------------------------------------------------------------------
    # Password management
    # ------------------------------------------------------------------

    @staticmethod
    def hash_password(plain: str) -> str:
        """Return a bcrypt hash of the plaintext password."""
        salt = _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
        return _bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify plaintext against a stored bcrypt hash."""
        try:
            return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Verify old password; update hash; return False if old password wrong."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            return False
        if not self.verify_password(old_password, user.hashed_password):
            return False
        new_hash = self.hash_password(new_password)
        self._user_repo.update(user_id, hashed_password=new_hash)
        return True

    # ------------------------------------------------------------------
    # First-run default admin
    # ------------------------------------------------------------------

    def create_default_admin(self) -> User:
        """Create the built-in admin account when the user table is empty."""
        import logging
        logging.getLogger(__name__).warning(
            "No users found. Creating default admin account. "
            "Change the password immediately!"
        )
        hashed = self.hash_password(DEFAULT_ADMIN_PASSWORD)
        return self._user_repo.create(
            username=DEFAULT_ADMIN_USERNAME,
            hashed_password=hashed,
            role=ROLE_ADMIN,
            display_name="Administrator",
        )

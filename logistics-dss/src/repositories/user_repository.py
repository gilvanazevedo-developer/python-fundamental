"""
User Repository
CRUD operations and lockout queries for the User ORM model.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import User


class UserRepository:
    """Data-access layer for User records."""

    def __init__(self):
        self._db = get_db_manager()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all(self, active_only: bool = True) -> list[User]:
        """Return all users ordered by username ASC."""
        with self._db.get_session() as session:
            q = session.query(User)
            if active_only:
                q = q.filter(User.active.is_(True))
            users = q.order_by(User.username.asc()).all()
            session.expunge_all()
            return users

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Return a single user by primary key, or None."""
        with self._db.get_session() as session:
            user = session.get(User, user_id)
            if user:
                session.expunge(user)
            return user

    def get_by_username(self, username: str) -> Optional[User]:
        """Case-insensitive exact match on username."""
        with self._db.get_session() as session:
            user = (
                session.query(User)
                .filter(func.lower(User.username) == username.lower())
                .first()
            )
            if user:
                session.expunge(user)
            return user

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create(
        self,
        username: str,
        hashed_password: str,
        role: str,
        display_name: Optional[str] = None,
    ) -> User:
        """Insert a new user row and commit. Raises IntegrityError on duplicate username."""
        with self._db.get_session() as session:
            user = User(
                username=username,
                hashed_password=hashed_password,
                role=role,
                display_name=display_name,
                active=True,
                failed_attempts=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            session.flush()          # surface IntegrityError before commit
            session.expunge(user)
            return user

    def update(self, user_id: int, **fields) -> Optional[User]:
        """Partial field update; sets updated_at automatically."""
        with self._db.get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return None
            for key, value in fields.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.utcnow()
            session.flush()
            session.expunge(user)
            return user

    def deactivate(self, user_id: int) -> bool:
        """Set active=False. Returns False if user not found."""
        with self._db.get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            user.active = False
            user.updated_at = datetime.utcnow()
            return True

    def increment_failed_attempts(self, user_id: int) -> int:
        """Atomically increment failed_attempts; return new count."""
        with self._db.get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return 0
            user.failed_attempts = (user.failed_attempts or 0) + 1
            count = user.failed_attempts
            return count

    def reset_failed_attempts(self, user_id: int) -> None:
        """Reset failed_attempts to 0 after a successful authentication."""
        with self._db.get_session() as session:
            user = session.get(User, user_id)
            if user:
                user.failed_attempts = 0

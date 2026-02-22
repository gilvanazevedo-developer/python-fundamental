"""
Unit tests for src/repositories/user_repository.py (T8-24)
7 tests covering CRUD, case-insensitive lookup, lockout counter, and active filtering.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.user_repository import UserRepository
from config.constants import ROLE_ADMIN, ROLE_VIEWER


@pytest.fixture
def user_repo(clean_database):
    """UserRepository wired to the isolated test DB."""
    return UserRepository()


@pytest.fixture
def sample_user(user_repo):
    """Create and return a standard test user."""
    return user_repo.create(
        username="gilvan",
        hashed_password="hashed_pw",
        role=ROLE_VIEWER,
        display_name="Gilvan Test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestUserRepository:

    def test_create_user_basic(self, user_repo):
        """create() inserts row; get_by_id() returns it with correct fields."""
        user = user_repo.create(
            username="alice",
            hashed_password="hash123",
            role=ROLE_ADMIN,
            display_name="Alice Smith",
        )
        assert user.id is not None
        fetched = user_repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.username == "alice"
        assert fetched.role == ROLE_ADMIN
        assert fetched.active is True
        assert fetched.failed_attempts == 0

    def test_create_user_duplicate_username_raises(self, user_repo):
        """Second create() with same username raises IntegrityError."""
        user_repo.create(username="bob", hashed_password="h1", role=ROLE_VIEWER)
        with pytest.raises(IntegrityError):
            user_repo.create(username="bob", hashed_password="h2", role=ROLE_VIEWER)

    def test_get_by_username_case_insensitive(self, user_repo, sample_user):
        """get_by_username('GILVAN') finds user with username='gilvan'."""
        found = user_repo.get_by_username("GILVAN")
        assert found is not None
        assert found.username == "gilvan"

        found_lower = user_repo.get_by_username("gilvan")
        assert found_lower is not None

        found_mixed = user_repo.get_by_username("GiLvAn")
        assert found_mixed is not None

    def test_deactivate_user(self, user_repo, sample_user):
        """deactivate() sets active=False; row still returned by get_by_id()."""
        result = user_repo.deactivate(sample_user.id)
        assert result is True

        fetched = user_repo.get_by_id(sample_user.id)
        assert fetched is not None
        assert fetched.active is False

    def test_increment_failed_attempts(self, user_repo, sample_user):
        """Three calls return 1, 2, 3; value persisted in DB."""
        c1 = user_repo.increment_failed_attempts(sample_user.id)
        c2 = user_repo.increment_failed_attempts(sample_user.id)
        c3 = user_repo.increment_failed_attempts(sample_user.id)
        assert c1 == 1
        assert c2 == 2
        assert c3 == 3
        fetched = user_repo.get_by_id(sample_user.id)
        assert fetched.failed_attempts == 3

    def test_reset_failed_attempts(self, user_repo, sample_user):
        """After 3 increments, reset_failed_attempts() sets failed_attempts=0."""
        for _ in range(3):
            user_repo.increment_failed_attempts(sample_user.id)
        user_repo.reset_failed_attempts(sample_user.id)
        fetched = user_repo.get_by_id(sample_user.id)
        assert fetched.failed_attempts == 0

    def test_get_all_active_only(self, user_repo):
        """get_all(active_only=True) excludes deactivated users."""
        u1 = user_repo.create(username="active_user", hashed_password="h", role=ROLE_VIEWER)
        u2 = user_repo.create(username="inactive_user", hashed_password="h", role=ROLE_VIEWER)
        user_repo.deactivate(u2.id)

        active = user_repo.get_all(active_only=True)
        ids = {u.id for u in active}
        assert u1.id in ids
        assert u2.id not in ids

        all_users = user_repo.get_all(active_only=False)
        all_ids = {u.id for u in all_users}
        assert u2.id in all_ids

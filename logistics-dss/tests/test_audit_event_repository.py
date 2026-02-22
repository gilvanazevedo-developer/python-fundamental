"""
Unit tests for src/repositories/audit_event_repository.py (T8-25)
6 tests covering create, filter, entity lookup, prune, and ordering.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.audit_event_repository import AuditEventRepository
from src.database.models import AuditEvent
from src.database.connection import get_db_manager


@pytest.fixture
def audit_repo(clean_database):
    """AuditEventRepository wired to the isolated test DB."""
    return AuditEventRepository()


def _insert_old_event(db, days_ago: int, actor: str = "system") -> None:
    """Helper: insert an event with occurred_at in the past."""
    with db.get_session() as session:
        event = AuditEvent(
            event_type="LOGIN",
            actor=actor,
            occurred_at=datetime.utcnow() - timedelta(days=days_ago),
        )
        session.add(event)


class TestAuditEventRepository:

    def test_create_audit_event(self, audit_repo):
        """create() inserts row with correct event_type, actor, and non-null occurred_at."""
        event = audit_repo.create(event_type="LOGIN", actor="alice")
        assert event.id is not None
        assert event.event_type == "LOGIN"
        assert event.actor == "alice"
        assert event.occurred_at is not None

    def test_get_by_event_type_filters(self, audit_repo):
        """get_by_event_type('LOGIN') returns only LOGIN events."""
        audit_repo.create(event_type="LOGIN",   actor="alice")
        audit_repo.create(event_type="LOGIN",   actor="bob")
        audit_repo.create(event_type="LOGOUT",  actor="alice")

        logins = audit_repo.get_by_event_type("LOGIN")
        assert all(e.event_type == "LOGIN" for e in logins)
        assert len(logins) == 2

        logouts = audit_repo.get_by_event_type("LOGOUT")
        assert len(logouts) == 1

    def test_get_for_entity(self, audit_repo):
        """get_for_entity('OptimizationRun', 1) returns only events for that entity."""
        audit_repo.create(
            event_type="OPTIMIZATION_RUN", actor="gilvan",
            entity_type="OptimizationRun", entity_id=1,
        )
        audit_repo.create(
            event_type="OPTIMIZATION_RUN", actor="gilvan",
            entity_type="OptimizationRun", entity_id=2,
        )
        audit_repo.create(event_type="LOGIN", actor="gilvan")

        entity_events = audit_repo.get_for_entity("OptimizationRun", 1)
        assert len(entity_events) == 1
        assert entity_events[0].entity_id == 1

    def test_get_by_actor(self, audit_repo):
        """get_by_actor('gilvan') excludes events by other actors."""
        audit_repo.create(event_type="LOGIN", actor="gilvan")
        audit_repo.create(event_type="LOGIN", actor="gilvan")
        audit_repo.create(event_type="LOGIN", actor="other_user")

        events = audit_repo.get_by_actor("gilvan")
        assert all(e.actor == "gilvan" for e in events)
        assert len(events) == 2

    def test_prune_old_events_count(self, clean_database, audit_repo):
        """Inserting 5 events (3 old, 2 recent): prune_old_events(30) deletes 3; returns 3."""
        db = get_db_manager()
        # 3 old events (35 days ago)
        _insert_old_event(db, 35, "system")
        _insert_old_event(db, 36, "system")
        _insert_old_event(db, 37, "system")
        # 2 recent events (< 30 days)
        audit_repo.create(event_type="LOGIN", actor="alice")
        audit_repo.create(event_type="LOGIN", actor="bob")

        deleted = audit_repo.prune_old_events(retention_days=30)
        assert deleted == 3

        remaining = audit_repo.get_all(limit=200)
        assert len(remaining) == 2

    def test_get_all_ordered_desc(self, clean_database, audit_repo):
        """get_all() returns events with most recent occurred_at first."""
        db = get_db_manager()
        _insert_old_event(db, 5, "alice")  # older
        audit_repo.create(event_type="LOGIN", actor="bob")  # newer

        events = audit_repo.get_all()
        assert len(events) >= 2
        # First event should be the newer one
        assert events[0].occurred_at >= events[1].occurred_at

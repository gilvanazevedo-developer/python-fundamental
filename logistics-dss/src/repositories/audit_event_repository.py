"""
Audit Event Repository
Write, filter, and prune operations for the AuditEvent ORM model.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import AuditEvent


class AuditEventRepository:
    """Data-access layer for AuditEvent records."""

    def __init__(self):
        self._db = get_db_manager()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create(
        self,
        event_type: str,
        actor: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        detail: Optional[str] = None,
    ) -> AuditEvent:
        """Insert a new audit event and commit. occurred_at defaults to utcnow()."""
        with self._db.get_session() as session:
            event = AuditEvent(
                event_type=event_type,
                actor=actor,
                entity_type=entity_type,
                entity_id=entity_id,
                detail=detail,
                occurred_at=datetime.utcnow(),
            )
            session.add(event)
            session.flush()
            session.expunge(event)
            return event

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all(self, limit: int = 200, offset: int = 0) -> list[AuditEvent]:
        """All events ordered by occurred_at DESC."""
        with self._db.get_session() as session:
            events = (
                session.query(AuditEvent)
                .order_by(AuditEvent.occurred_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            session.expunge_all()
            return events

    def get_by_event_type(self, event_type: str, limit: int = 100) -> list[AuditEvent]:
        """Filtered by event_type; ordered by occurred_at DESC."""
        with self._db.get_session() as session:
            events = (
                session.query(AuditEvent)
                .filter(AuditEvent.event_type == event_type)
                .order_by(AuditEvent.occurred_at.desc())
                .limit(limit)
                .all()
            )
            session.expunge_all()
            return events

    def get_by_actor(self, username: str, limit: int = 100) -> list[AuditEvent]:
        """Events by a specific actor; ordered by occurred_at DESC."""
        with self._db.get_session() as session:
            events = (
                session.query(AuditEvent)
                .filter(AuditEvent.actor == username)
                .order_by(AuditEvent.occurred_at.desc())
                .limit(limit)
                .all()
            )
            session.expunge_all()
            return events

    def get_for_entity(self, entity_type: str, entity_id: int) -> list[AuditEvent]:
        """All events referencing a specific entity row."""
        with self._db.get_session() as session:
            events = (
                session.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type == entity_type,
                    AuditEvent.entity_id == entity_id,
                )
                .order_by(AuditEvent.occurred_at.desc())
                .all()
            )
            session.expunge_all()
            return events

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def prune_old_events(self, retention_days: int) -> int:
        """Delete events where occurred_at < now() - retention_days. Returns deleted count."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        with self._db.get_session() as session:
            deleted = (
                session.query(AuditEvent)
                .filter(AuditEvent.occurred_at < cutoff)
                .delete(synchronize_session=False)
            )
            return deleted

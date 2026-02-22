"""
Audit Service
Unified event-logging facade called by all state-changing operations.
"""

import json
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.audit_event_repository import AuditEventRepository
from config.constants import AUDIT_RETENTION_DAYS


class AuditService:
    """Write and query the audit event trail."""

    def __init__(self):
        self._repo = AuditEventRepository()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log(
        self,
        event_type: str,
        actor: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        detail: Optional[dict] = None,
    ):
        """Serialise detail dict to JSON and persist an AuditEvent row."""
        detail_str = json.dumps(detail) if detail else None
        return self._repo.create(
            event_type=event_type,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail_str,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_recent_events(self, limit: int = 200) -> list[dict]:
        """Serialised recent events for AuditLogView."""
        events = self._repo.get_all(limit=limit)
        return [self._to_dict(e) for e in events]

    def get_events_for_entity(self, entity_type: str, entity_id: int) -> list[dict]:
        """Event history for a specific entity row."""
        events = self._repo.get_for_entity(entity_type, entity_id)
        return [self._to_dict(e) for e in events]

    def get_events_by_actor(self, username: str) -> list[dict]:
        """Activity history for a specific user."""
        events = self._repo.get_by_actor(username)
        return [self._to_dict(e) for e in events]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def prune_old_events(self) -> int:
        """Delete events older than AUDIT_RETENTION_DAYS. Called by weekly scheduler job."""
        return self._repo.prune_old_events(AUDIT_RETENTION_DAYS)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(event) -> dict:
        detail = None
        if event.detail:
            try:
                detail = json.loads(event.detail)
            except (json.JSONDecodeError, TypeError):
                detail = event.detail
        return {
            "id":          event.id,
            "event_type":  event.event_type,
            "actor":       event.actor,
            "entity_type": event.entity_type,
            "entity_id":   event.entity_id,
            "detail":      detail,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        }

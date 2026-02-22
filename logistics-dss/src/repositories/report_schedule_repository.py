"""
Report Schedule Repository
CRUD + run-history operations for the ReportSchedule ORM model.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import ReportSchedule

_VALID_REPORT_TYPES = {"INVENTORY", "FORECAST", "POLICY", "EXECUTIVE"}
_VALID_FORMATS      = {"PDF", "EXCEL"}


class ReportScheduleRepository:
    """Data-access layer for ReportSchedule records."""

    def __init__(self):
        self._db = get_db_manager()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all(self, active_only: bool = False) -> list[ReportSchedule]:
        """All schedules ordered by id ASC."""
        with self._db.get_session() as session:
            q = session.query(ReportSchedule)
            if active_only:
                q = q.filter(ReportSchedule.active.is_(True))
            schedules = q.order_by(ReportSchedule.id.asc()).all()
            session.expunge_all()
            return schedules

    def get_by_id(self, schedule_id: int) -> Optional[ReportSchedule]:
        """Single schedule by PK, or None."""
        with self._db.get_session() as session:
            sched = session.get(ReportSchedule, schedule_id)
            if sched:
                session.expunge(sched)
            return sched

    def get_active(self) -> list[ReportSchedule]:
        """All schedules with active=True; used at scheduler startup."""
        return self.get_all(active_only=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create(
        self,
        report_type: str,
        export_format: str,
        cron_expression: str,
        output_dir: str,
        created_by: str,
    ) -> ReportSchedule:
        """Insert a new schedule and commit."""
        with self._db.get_session() as session:
            sched = ReportSchedule(
                report_type=report_type,
                export_format=export_format,
                cron_expression=cron_expression,
                output_dir=output_dir,
                created_by=created_by,
                active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(sched)
            session.flush()
            session.expunge(sched)
            return sched

    def update(self, schedule_id: int, **fields) -> Optional[ReportSchedule]:
        """Partial update; validates report_type and export_format if changed."""
        if "report_type" in fields and fields["report_type"] not in _VALID_REPORT_TYPES:
            raise ValueError(f"Invalid report_type: {fields['report_type']}")
        if "export_format" in fields and fields["export_format"] not in _VALID_FORMATS:
            raise ValueError(f"Invalid export_format: {fields['export_format']}")

        with self._db.get_session() as session:
            sched = session.get(ReportSchedule, schedule_id)
            if not sched:
                return None
            for key, value in fields.items():
                if hasattr(sched, key):
                    setattr(sched, key, value)
            sched.updated_at = datetime.utcnow()
            session.flush()
            session.expunge(sched)
            return sched

    def deactivate(self, schedule_id: int) -> bool:
        """Set active=False. Returns False if not found."""
        with self._db.get_session() as session:
            sched = session.get(ReportSchedule, schedule_id)
            if not sched:
                return False
            sched.active = False
            sched.updated_at = datetime.utcnow()
            return True

    def record_run(self, schedule_id: int, status: str) -> Optional[ReportSchedule]:
        """Set last_run_at = utcnow() and last_run_status = status."""
        with self._db.get_session() as session:
            sched = session.get(ReportSchedule, schedule_id)
            if not sched:
                return None
            sched.last_run_at = datetime.utcnow()
            sched.last_run_status = status
            sched.updated_at = datetime.utcnow()
            session.flush()
            session.expunge(sched)
            return sched

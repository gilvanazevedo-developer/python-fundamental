"""
Scheduler Service
APScheduler integration with cron validation and thread-safe UI notification queue.

Thread-safety contract: _run_scheduled_report() executes in a background thread
and must NEVER make Tkinter calls. All UI updates are routed through _update_queue;
the main thread polls via App.after(SCHEDULER_QUEUE_POLL_MS, ...).
"""

import queue
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.repositories.report_schedule_repository import ReportScheduleRepository
from src.services.audit_service import AuditService
from config.constants import (
    MIN_SCHEDULE_INTERVAL_SECONDS,
    AUDIT_PRUNE_CRON,
)

# Module-level queue so background thread can post without holding references to Tkinter.
_update_queue: queue.Queue = queue.Queue()


def get_update_queue() -> queue.Queue:
    """Return the module-level scheduler notification queue."""
    return _update_queue


class SchedulerService:
    """Manage scheduled report jobs using APScheduler."""

    def __init__(self, report_runner: Optional[Callable] = None):
        """
        Parameters
        ----------
        report_runner:
            Callable(report_type, export_format, output_dir) that generates a report.
            Defaults to a no-op stub when omitted (useful in tests that mock it).
        """
        self._schedule_repo = ReportScheduleRepository()
        self._audit = AuditService()
        self._report_runner: Callable = report_runner or self._default_runner
        self._scheduler: Optional[BackgroundScheduler] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start APScheduler; load all active schedules; add weekly audit prune job."""
        if self._scheduler and self._scheduler.running:
            return

        self._scheduler = BackgroundScheduler(daemon=True)

        # Register all active report schedules
        for sched in self._schedule_repo.get_active():
            self._register_job(sched.id, sched.cron_expression)

        # Weekly audit event prune: Sunday 02:00 UTC
        self._scheduler.add_job(
            func=self._audit.prune_old_events,
            trigger=CronTrigger.from_crontab(AUDIT_PRUNE_CRON),
            id="audit_prune",
            replace_existing=True,
        )

        self._scheduler.start()

    def stop(self) -> None:
        """Shut down APScheduler gracefully. Called on app exit."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def create_schedule(
        self,
        report_type: str,
        export_format: str,
        cron_expression: str,
        output_dir: str,
        created_by: str = "system",
    ) -> dict:
        """Validate cron, persist ReportSchedule row, register APScheduler job."""
        self._validate_cron(cron_expression)

        sched = self._schedule_repo.create(
            report_type=report_type,
            export_format=export_format,
            cron_expression=cron_expression,
            output_dir=output_dir,
            created_by=created_by,
        )

        if self._scheduler and self._scheduler.running:
            self._register_job(sched.id, cron_expression)

        return self._to_dict(sched)

    def update_schedule(self, schedule_id: int, **fields) -> Optional[dict]:
        """Re-validate cron if changed; update DB row; reschedule APScheduler job."""
        if "cron_expression" in fields:
            self._validate_cron(fields["cron_expression"])

        sched = self._schedule_repo.update(schedule_id, **fields)
        if not sched:
            return None

        if self._scheduler and self._scheduler.running:
            job_id = f"report_{schedule_id}"
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
            if sched.active:
                self._register_job(sched.id, sched.cron_expression)

        return self._to_dict(sched)

    def deactivate_schedule(self, schedule_id: int) -> bool:
        """Set active=False; remove APScheduler job."""
        result = self._schedule_repo.deactivate(schedule_id)
        if result and self._scheduler and self._scheduler.running:
            job_id = f"report_{schedule_id}"
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
        return result

    def get_all_schedules(self) -> list[dict]:
        """Serialised schedule list with next_run_time from APScheduler."""
        schedules = self._schedule_repo.get_all(active_only=False)
        result = []
        for s in schedules:
            d = self._to_dict(s)
            if self._scheduler and self._scheduler.running:
                job = self._scheduler.get_job(f"report_{s.id}")
                d["next_run_time"] = (
                    job.next_run_time.isoformat() if job and job.next_run_time else None
                )
            else:
                d["next_run_time"] = None
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Background job
    # ------------------------------------------------------------------

    def _run_scheduled_report(self, schedule_id: int) -> None:
        """
        Execute in APScheduler background thread — NO Tkinter calls allowed.
        Posts result to _update_queue for main-thread polling.
        """
        try:
            sched = self._schedule_repo.get_by_id(schedule_id)
            if not sched:
                return

            self._report_runner(sched.report_type, sched.export_format, sched.output_dir)
            self._schedule_repo.record_run(schedule_id, "SUCCESS")
            self._audit.log(
                "SCHEDULE_RUN",
                actor="scheduler",
                entity_type="ReportSchedule",
                entity_id=schedule_id,
                detail={"status": "SUCCESS", "report_type": sched.report_type},
            )
            _update_queue.put({
                "type": "SCHEDULE_RUN",
                "schedule_id": schedule_id,
                "status": "SUCCESS",
            })
        except Exception as exc:
            self._schedule_repo.record_run(schedule_id, "FAILURE")
            _update_queue.put({
                "type": "SCHEDULE_RUN",
                "schedule_id": schedule_id,
                "status": "FAILURE",
                "error": str(exc),
            })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _register_job(self, schedule_id: int, cron_expression: str) -> None:
        self._scheduler.add_job(
            func=self._run_scheduled_report,
            trigger=CronTrigger.from_crontab(cron_expression),
            args=[schedule_id],
            id=f"report_{schedule_id}",
            replace_existing=True,
        )

    def _validate_cron(self, expression: str) -> None:
        """Raise ValueError for invalid syntax or schedules more frequent than 1 hour."""
        try:
            trigger = CronTrigger.from_crontab(expression)
        except (ValueError, Exception) as exc:
            raise ValueError(f"Invalid cron expression '{expression}': {exc}")

        now = datetime.utcnow()
        t1 = trigger.get_next_fire_time(None, now)
        t2 = trigger.get_next_fire_time(t1, t1) if t1 else None
        if t1 and t2 and (t2 - t1).total_seconds() < MIN_SCHEDULE_INTERVAL_SECONDS:
            mins = int((t2 - t1).total_seconds() / 60)
            raise ValueError(
                f"Schedule interval too short ({mins} min). "
                f"Minimum is {MIN_SCHEDULE_INTERVAL_SECONDS // 3600} hour(s)."
            )

    @staticmethod
    def _to_dict(sched) -> dict:
        return {
            "id":              sched.id,
            "report_type":     sched.report_type,
            "export_format":   sched.export_format,
            "cron_expression": sched.cron_expression,
            "output_dir":      sched.output_dir,
            "active":          sched.active,
            "last_run_at":     sched.last_run_at.isoformat() if sched.last_run_at else None,
            "last_run_status": sched.last_run_status,
            "created_by":      sched.created_by,
        }

    @staticmethod
    def _default_runner(report_type: str, export_format: str, output_dir: str) -> None:
        """Stub runner used when no report_runner is injected."""
        pass

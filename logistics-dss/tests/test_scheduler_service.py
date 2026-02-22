"""
Unit tests for src/services/scheduler_service.py (T8-29)
7 tests covering schedule creation, deactivation, cron validation, and job execution.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.scheduler_service import SchedulerService, _update_queue
from src.repositories.report_schedule_repository import ReportScheduleRepository


@pytest.fixture(autouse=True)
def drain_queue():
    """Drain the module-level notification queue before/after each test."""
    while not _update_queue.empty():
        _update_queue.get_nowait()
    yield
    while not _update_queue.empty():
        _update_queue.get_nowait()


@pytest.fixture
def mock_runner():
    """A callable mock used as the report runner."""
    return MagicMock()


@pytest.fixture
def svc(clean_database, mock_runner):
    """SchedulerService with an isolated DB and mock runner (scheduler not started)."""
    return SchedulerService(report_runner=mock_runner)


@pytest.fixture
def started_svc(svc):
    """Start the scheduler; stop it after the test."""
    svc.start()
    yield svc
    svc.stop()


class TestSchedulerService:

    def test_create_schedule_persists(self, svc):
        """create_schedule() creates ReportSchedule row; get_all_schedules() includes it."""
        d = svc.create_schedule(
            report_type="INVENTORY",
            export_format="PDF",
            cron_expression="0 8 * * 1",
            output_dir="/tmp",
            created_by="admin",
        )
        assert d["id"] is not None
        assert d["report_type"] == "INVENTORY"
        assert d["active"] is True

        schedules = svc.get_all_schedules()
        ids = [s["id"] for s in schedules]
        assert d["id"] in ids

    def test_deactivate_schedule(self, started_svc):
        """deactivate_schedule() sets active=False; job removed from APScheduler job list."""
        d = started_svc.create_schedule(
            report_type="FORECAST",
            export_format="EXCEL",
            cron_expression="0 9 * * *",
            output_dir="/tmp",
            created_by="admin",
        )
        schedule_id = d["id"]

        result = started_svc.deactivate_schedule(schedule_id)
        assert result is True

        schedules = started_svc.get_all_schedules()
        target = next((s for s in schedules if s["id"] == schedule_id), None)
        assert target is not None
        assert target["active"] is False

        # APScheduler job should be removed
        job = started_svc._scheduler.get_job(f"report_{schedule_id}")
        assert job is None

    def test_invalid_cron_raises(self, svc):
        """create_schedule(cron_expression='not-a-cron') raises ValueError."""
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            svc.create_schedule(
                report_type="POLICY",
                export_format="PDF",
                cron_expression="not-a-cron",
                output_dir="/tmp",
                created_by="admin",
            )

    def test_too_frequent_cron_raises(self, svc):
        """cron_expression='*/30 * * * *' (30-min interval) raises ValueError."""
        with pytest.raises(ValueError, match="[Ss]hort|[Mm]inimum|[Ii]nterval"):
            svc.create_schedule(
                report_type="POLICY",
                export_format="PDF",
                cron_expression="*/30 * * * *",
                output_dir="/tmp",
                created_by="admin",
            )

    def test_run_scheduled_report_calls_runner(self, svc, mock_runner, clean_database):
        """_run_scheduled_report() with mocked runner verifies generate() called once."""
        d = svc.create_schedule(
            report_type="INVENTORY",
            export_format="PDF",
            cron_expression="0 8 * * 1",
            output_dir="/tmp/out",
            created_by="admin",
        )
        svc._run_scheduled_report(d["id"])
        mock_runner.assert_called_once_with("INVENTORY", "PDF", "/tmp/out")

    def test_run_records_success_status(self, svc, mock_runner, clean_database):
        """After _run_scheduled_report() with mock success: record_run called with 'SUCCESS'."""
        d = svc.create_schedule(
            report_type="INVENTORY",
            export_format="PDF",
            cron_expression="0 8 * * 1",
            output_dir="/tmp",
            created_by="admin",
        )
        svc._run_scheduled_report(d["id"])

        repo = ReportScheduleRepository()
        fetched = repo.get_by_id(d["id"])
        assert fetched.last_run_status == "SUCCESS"
        assert fetched.last_run_at is not None

    def test_run_records_failure_on_exception(self, svc, mock_runner, clean_database):
        """ReportRunner raises IOError → record_run called with 'FAILURE'; exception swallowed."""
        mock_runner.side_effect = IOError("disk full")

        d = svc.create_schedule(
            report_type="POLICY",
            export_format="EXCEL",
            cron_expression="0 8 * * 1",
            output_dir="/tmp",
            created_by="admin",
        )
        # Must not propagate the IOError
        svc._run_scheduled_report(d["id"])

        repo = ReportScheduleRepository()
        fetched = repo.get_by_id(d["id"])
        assert fetched.last_run_status == "FAILURE"

        # Notification posted to queue with FAILURE status
        msg = _update_queue.get_nowait()
        assert msg["status"] == "FAILURE"

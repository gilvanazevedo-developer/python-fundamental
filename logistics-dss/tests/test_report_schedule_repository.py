"""
Unit tests for src/repositories/report_schedule_repository.py (T8-26)
7 tests covering CRUD, active filtering, deactivation, and run recording.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.report_schedule_repository import ReportScheduleRepository


@pytest.fixture
def sched_repo(clean_database):
    """ReportScheduleRepository wired to the isolated test DB."""
    return ReportScheduleRepository()


@pytest.fixture
def sample_schedule(sched_repo):
    return sched_repo.create(
        report_type="INVENTORY",
        export_format="PDF",
        cron_expression="0 8 * * 1",
        output_dir="/tmp/reports",
        created_by="admin",
    )


class TestReportScheduleRepository:

    def test_create_schedule(self, sched_repo):
        """create() inserts row; get_by_id() returns with correct cron_expression and active=True."""
        s = sched_repo.create(
            report_type="FORECAST",
            export_format="EXCEL",
            cron_expression="0 9 * * *",
            output_dir="/reports",
            created_by="admin",
        )
        assert s.id is not None

        fetched = sched_repo.get_by_id(s.id)
        assert fetched is not None
        assert fetched.cron_expression == "0 9 * * *"
        assert fetched.active is True
        assert fetched.last_run_at is None
        assert fetched.last_run_status is None

    def test_get_all_active_only(self, sched_repo, sample_schedule):
        """get_all(active_only=True) excludes deactivated schedules."""
        inactive = sched_repo.create(
            report_type="POLICY",
            export_format="PDF",
            cron_expression="0 7 * * *",
            output_dir="/tmp",
            created_by="admin",
        )
        sched_repo.deactivate(inactive.id)

        active = sched_repo.get_all(active_only=True)
        active_ids = {s.id for s in active}
        assert sample_schedule.id in active_ids
        assert inactive.id not in active_ids

    def test_deactivate_schedule(self, sched_repo, sample_schedule):
        """deactivate() sets active=False; schedule absent from get_active()."""
        result = sched_repo.deactivate(sample_schedule.id)
        assert result is True

        active = sched_repo.get_active()
        ids = {s.id for s in active}
        assert sample_schedule.id not in ids

        fetched = sched_repo.get_by_id(sample_schedule.id)
        assert fetched.active is False

    def test_record_run_success(self, sched_repo, sample_schedule):
        """record_run(schedule_id, 'SUCCESS') sets last_run_at to non-null datetime."""
        updated = sched_repo.record_run(sample_schedule.id, "SUCCESS")
        assert updated is not None
        assert updated.last_run_at is not None
        assert updated.last_run_status == "SUCCESS"

    def test_record_run_failure(self, sched_repo, sample_schedule):
        """record_run(schedule_id, 'FAILURE') sets last_run_status='FAILURE'."""
        updated = sched_repo.record_run(sample_schedule.id, "FAILURE")
        assert updated.last_run_status == "FAILURE"

    def test_update_schedule_cron(self, sched_repo, sample_schedule):
        """update(schedule_id, cron_expression='0 9 * * *') persists new expression."""
        updated = sched_repo.update(sample_schedule.id, cron_expression="0 9 * * *")
        assert updated is not None
        assert updated.cron_expression == "0 9 * * *"

        fetched = sched_repo.get_by_id(sample_schedule.id)
        assert fetched.cron_expression == "0 9 * * *"

    def test_get_all_returns_all_statuses(self, sched_repo, sample_schedule):
        """get_all(active_only=False) returns both active and inactive schedules."""
        inactive = sched_repo.create(
            report_type="EXECUTIVE",
            export_format="PDF",
            cron_expression="0 6 * * 0",
            output_dir="/tmp",
            created_by="admin",
        )
        sched_repo.deactivate(inactive.id)

        all_scheds = sched_repo.get_all(active_only=False)
        ids = {s.id for s in all_scheds}
        assert sample_schedule.id in ids
        assert inactive.id in ids

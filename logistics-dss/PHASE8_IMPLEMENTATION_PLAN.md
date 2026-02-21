# Logistics DSS - Phase 8 Implementation Plan
# Productionisation: Authentication, Scheduler, Import Wizard & Packaging

**Project:** Logistics Decision Support System
**Phase:** 8 of 8 — Productionisation: Authentication, Scheduler, Import Wizard & Packaging
**Author:** Gilvan de Azevedo
**Date:** 2026-02-21
**Status:** Not Started
**Depends on:** Phase 7 (Supplier & Purchase Order Management) — functionally complete

---

## 1. Phase 8 Objective

Phase 8 is the final phase of the Logistics DSS. It transforms the analytically complete, procurement-enabled system from Phases 1–7 into a production-ready desktop application with four major capability additions.

**User Authentication and Role-Based Access Control (RBAC):**
A `User` ORM model introduces `username`, `hashed_password` (bcrypt), and `role (ADMIN | BUYER | VIEWER)`. A `LoginView` replaces the current direct-launch startup, gating the main application behind credential verification. Every view and service operation respects the authenticated user's role: VIEWER has read-only access, BUYER has the full PO workflow, and ADMIN has unrestricted access including user management and database administration.

**Data Import Wizard:**
An `ImportWizardView` provides a five-step guided import for three data types: product master (SKU, name, costs), historical demand (SKU, date, quantity), and supplier master (name, lead time, contact). The wizard validates each row before committing, shows a preview of the first ten records, and reports imported and skipped counts. Phase 6's `ExcelExporter` and the existing CSV importers provide the infrastructure; Phase 8 unifies them behind a single `ImportWizardService` orchestrator.

**Scheduled Report Generation:**
A `ReportSchedule` ORM model stores per-schedule configuration: `report_type`, `export_format`, `cron_expression`, `output_dir`, and `active`. An `APScheduler`-backed `SchedulerService` registers each active schedule as a background job, calls Phase 6's `ReportRunner.generate()` in a worker thread, and posts results back to the Tkinter main thread via a thread-safe queue. Scheduler status and the full schedule list are visible in the new `SettingsView`.

**System Settings, Audit Trail, and Packaging:**
A `SettingsView` exposes database path, log level, export directory, theme, and language preferences — persisted in `config/settings.json`. An `AuditEvent` ORM model records login/logout, PO status changes, optimisation runs, report generation, and import completions — displayed in an `AuditLogView` accessible to ADMIN users only. A scheduled weekly `AuditEvent` pruning job enforces `AUDIT_RETENTION_DAYS` (default 365). Finally, a PyInstaller spec and `pyproject.toml` produce a distributable single-file executable for Windows (`.exe`) and macOS (`.app`), and a pip-installable package.

**Deliverables:**
- `User` ORM model: username, bcrypt-hashed password, role, lockout support
- `ReportSchedule` ORM model: cron-based report scheduling with run history
- `AuditEvent` ORM model: unified event log across all operational domains
- `UserRepository`, `AuditEventRepository`, `ReportScheduleRepository`: clean query layer
- `AuthService`: login, logout, session state, password hashing, lockout enforcement
- `AuditService`: event logging called by existing services after all state-changing operations
- `SettingsService`: `settings.json` I/O with typed defaults
- `SchedulerService`: APScheduler integration, cron validation, thread-safe UI notification queue
- `ImportWizardService`: validation, preview, and import orchestration for three data types
- `LoginView`: login form + startup gate + first-run default admin creation
- `SettingsView`: general settings + scheduled reports panel + user management table
- `ImportWizardView`: five-step guided import wizard
- `AuditLogView`: paginated audit trail table (ADMIN role only)
- `App` extension: login gate, current-user injection, RBAC enforcement across all views
- `packaging/logistics_dss.spec`: PyInstaller build spec
- `packaging/pyproject.toml`: pip-installable distribution config
- Full test suite (56 new tests): auth, audit, scheduler, import wizard, RBAC

---

## 2. Phase 7 Dependencies (Available)

Phase 8 builds directly on the following Phase 7 (and prior) components:

| Component | Module | Usage in Phase 8 |
|---|---|---|
| `PurchaseOrder` ORM | `src/database/models.py` | `created_by` field populated with `User.username` after login gate active |
| `PurchaseOrderService` | `src/services/purchase_order_service.py` | All state-changing methods emit `AuditEvent` via `AuditService`; RBAC checked on `create_po()`, `cancel_po()` |
| `SupplierService` | `src/services/supplier_service.py` | `create_supplier()`, `deactivate_supplier()` emit `AuditEvent`; RBAC checked (ADMIN only for deactivation) |
| `OptimizationService` | `src/services/optimization_service.py` | `run_optimization()` emits `AuditEvent`; restricted to BUYER and ADMIN roles |
| `ReportRunner` | `src/reporting/report_runner.py` | Called by `SchedulerService._run_scheduled_report()` in background thread; no UI dependency required |
| `KPIService` | `src/services/kpi_service.py` | Unchanged; procurement KPIs feed Settings view system health widget |
| `ExcelExporter` | `src/reporting/excel_exporter.py` | Reused by `ImportWizardService` for the Excel import path |
| `DataTable` | `src/ui/widgets/data_table.py` | Audit log table, user management table, scheduled reports table |
| `KPICard` | `src/ui/widgets/kpi_card.py` | System health KPIs in `SettingsView` header |
| `LoggerMixin` | `src/logger.py` | Logging in all new Phase 8 modules |
| `DatabaseManager` | `src/database/connection.py` | Session handling for all new repositories |
| Constants | `config/constants.py` | Extended with auth, audit, scheduler, and import constants |
| `_VALID_TRANSITIONS` pattern | `src/services/purchase_order_service.py` | Adopted for `ReportSchedule` status workflow in `SchedulerService` |
| `SupplierPerformanceRecord` + `ReportLog` | `src/database/models.py` | Integrated into the unified `AuditEvent` trail (not replaced; cross-referenced) |

---

## 3. Architecture Overview

### 3.1 Phase 8 Directory Structure

```
logistics-dss/
├── config/
│   ├── constants.py            # + auth, audit, scheduler, import constants
│   └── settings.json           # NEW: runtime settings (db_path, theme, log_level, export_dir, language)
├── packaging/                  # NEW directory
│   ├── logistics_dss.spec      # NEW: PyInstaller build spec
│   └── pyproject.toml          # NEW: pip-installable distribution config
├── src/
│   ├── database/
│   │   └── models.py           # + User, ReportSchedule, AuditEvent ORM models
│   ├── repositories/
│   │   ├── user_repository.py              # NEW: CRUD + lockout queries
│   │   ├── audit_event_repository.py       # NEW: write + filter + prune
│   │   └── report_schedule_repository.py   # NEW: CRUD + run-history recording
│   ├── services/
│   │   ├── auth_service.py                 # NEW: login, logout, session state, password hashing
│   │   ├── audit_service.py                # NEW: event logging across all domains
│   │   ├── settings_service.py             # NEW: settings.json I/O with typed defaults
│   │   ├── scheduler_service.py            # NEW: APScheduler integration + cron validation
│   │   ├── import_wizard_service.py        # NEW: validation, preview, import for 3 data types
│   │   ├── purchase_order_service.py       # (existing) + AuditService calls + RBAC + created_by
│   │   ├── supplier_service.py             # (existing) + AuditService calls + RBAC
│   │   └── optimization_service.py         # (existing) + AuditService call on run_optimization()
│   └── ui/
│       ├── app.py                          # + LoginView gate + current_user injection + RBAC + scheduler start
│       └── views/
│           ├── login_view.py               # NEW: login form + startup gate + first-run wizard
│           ├── settings_view.py            # NEW: general settings + scheduled reports + user management
│           ├── import_wizard_view.py       # NEW: five-step guided import wizard
│           ├── audit_log_view.py           # NEW: paginated audit trail (ADMIN only)
│           ├── purchase_orders_view.py     # (existing) + RBAC button visibility
│           ├── suppliers_view.py           # (existing) + RBAC button visibility
│           ├── alerts_view.py              # (existing) + RBAC on "Create PO Draft" button
│           ├── optimization_view.py        # (existing) + RBAC on "Run Optimization" button
│           └── executive_view.py           # (existing, unchanged)
├── tests/
│   ├── test_user_repository.py             # NEW: 7 tests
│   ├── test_audit_event_repository.py      # NEW: 6 tests
│   ├── test_report_schedule_repository.py  # NEW: 7 tests
│   ├── test_auth_service.py                # NEW: 9 tests
│   ├── test_settings_service.py            # NEW: 6 tests
│   ├── test_scheduler_service.py           # NEW: 7 tests
│   ├── test_import_wizard.py               # NEW: 8 tests
│   └── test_rbac_enforcement.py            # NEW: 6 tests
└── main.py                                 # (existing)
```

### 3.2 Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                             Presentation Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │Dashboard │  │Forecast  │  │Optimiz.  │  │ Alerts   │  │  Executive   │  │
│  │  View    │  │  View    │  │View (R)  │  │View (R)  │  │    View      │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐ │
│  │Suppliers │  │Purchase  │  │ Reports  │  │  NEW Views                   │ │
│  │View (R)  │  │Orders (R)│  │   View   │  │  LoginView  SettingsView     │ │
│  └──────────┘  └──────────┘  └──────────┘  │  ImportWizardView           │ │
│                                             │  AuditLogView (ADMIN only)  │ │
│                                             └──────────────────────────────┘ │
│  (R) = RBAC-aware: buttons shown/hidden based on current_user.role           │
├──────────────────────────────────────────────────────────────────────────────┤
│                              Service Layer                                     │
│  ┌────────────┐ ┌───────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │AuthService │ │AuditSvc   │ │SettingsService│ │SchedulerService (NEW)   │  │
│  │  (NEW)     │ │  (NEW)    │ │   (NEW)       │ │ + APScheduler           │  │
│  └────────────┘ └───────────┘ └──────────────┘ └─────────────────────────┘  │
│  ┌────────────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ImportWizardService │  │PurchaseOrd.│  │ Supplier   │  │ Optimization  │  │
│  │      (NEW)         │  │ Svc (+)    │  │  Svc (+)   │  │   Svc (+)     │  │
│  └────────────────────┘  └────────────┘  └────────────┘  └───────────────┘  │
├──────────────────────────────────────────────────────────────────────────────┤
│                            Repository Layer                                    │
│  ┌────────────────┐  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │UserRepository  │  │AuditEventRepository  │  │ReportScheduleRepository  │  │
│  │    (NEW)       │  │      (NEW)           │  │         (NEW)            │  │
│  └────────────────┘  └─────────────────────┘  └──────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────────┤
│                         ORM / Database Layer                                   │
│  ┌────────┐  ┌────────────────┐  ┌────────────┐  ┌───────────────────────┐  │
│  │  User  │  │ ReportSchedule │  │ AuditEvent │  │  All Phase 1–7 models │  │
│  │ (NEW)  │  │    (NEW)       │  │   (NEW)    │  │      (unchanged)      │  │
│  └────────┘  └────────────────┘  └────────────┘  └───────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Database Models

#### 4.1.1 `User`

```python
class User(Base):
    __tablename__ = "user"

    id               = Column(Integer,  primary_key=True, autoincrement=True)
    username         = Column(String(64),  nullable=False, unique=True)
    display_name     = Column(String(128), nullable=True)
    hashed_password  = Column(String(256), nullable=False)
    role             = Column(String(16),  nullable=False)
    # ADMIN | BUYER | VIEWER
    active           = Column(Boolean,     nullable=False, default=True)
    failed_attempts  = Column(Integer,     nullable=False, default=0)
    # reset to 0 on successful login; lockout at MAX_LOGIN_ATTEMPTS
    last_login_at    = Column(DateTime,    nullable=True)
    created_at       = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at       = Column(DateTime,    nullable=False, default=datetime.utcnow,
                                           onupdate=datetime.utcnow)
```

**Indexes:**
- `(username)` — UNIQUE (enforced by constraint)
- `(active, role)` — active users by role for RBAC queries
- `(failed_attempts)` — quick lockout check

---

#### 4.1.2 `ReportSchedule`

```python
class ReportSchedule(Base):
    __tablename__ = "report_schedule"

    id                = Column(Integer,    primary_key=True, autoincrement=True)
    report_type       = Column(String(32), nullable=False)
    # INVENTORY | FORECAST | POLICY | EXECUTIVE
    export_format     = Column(String(8),  nullable=False)
    # PDF | EXCEL
    cron_expression   = Column(String(64), nullable=False)
    # Standard 5-field cron: "0 8 * * 1" = every Monday at 08:00
    output_dir        = Column(String(512), nullable=False)
    active            = Column(Boolean,    nullable=False, default=True)
    last_run_at       = Column(DateTime,   nullable=True)
    last_run_status   = Column(String(16), nullable=True)
    # SUCCESS | FAILURE | None (never run)
    created_by        = Column(String(128), nullable=False)
    created_at        = Column(DateTime,   nullable=False, default=datetime.utcnow)
    updated_at        = Column(DateTime,   nullable=False, default=datetime.utcnow,
                                           onupdate=datetime.utcnow)
```

**Indexes:**
- `(active, report_type)` — active schedules by type for scheduler startup
- `(last_run_at DESC)` — most recently executed schedules

---

#### 4.1.3 `AuditEvent`

```python
class AuditEvent(Base):
    __tablename__ = "audit_event"

    id           = Column(Integer,    primary_key=True, autoincrement=True)
    event_type   = Column(String(32), nullable=False)
    # LOGIN | LOGOUT | PO_STATUS_CHANGE | OPTIMIZATION_RUN | REPORT_GENERATED |
    # SUPPLIER_CREATED | SUPPLIER_DEACTIVATED | IMPORT_COMPLETED | SETTINGS_CHANGED |
    # USER_CREATED | USER_DEACTIVATED | SCHEDULE_RUN
    actor        = Column(String(128), nullable=False)
    # username of the authenticated user performing the action
    entity_type  = Column(String(32),  nullable=True)
    # "PurchaseOrder" | "Supplier" | "OptimizationRun" | "ReportSchedule" | None
    entity_id    = Column(Integer,     nullable=True)
    # Primary key of the affected row; NULL for session events (LOGIN/LOGOUT)
    detail       = Column(Text,        nullable=True)
    # JSON-serialised supplementary context
    # e.g. {"from_status": "SUBMITTED", "to_status": "CONFIRMED"} for PO_STATUS_CHANGE
    occurred_at  = Column(DateTime,    nullable=False, default=datetime.utcnow)
```

**Indexes:**
- `(event_type, occurred_at DESC)` — filtered event feed by type
- `(actor, occurred_at DESC)` — per-user activity history
- `(entity_type, entity_id)` — all events for a specific entity
- `(occurred_at)` — range queries for pruning old events

**`PurchaseOrder` model extension:**

```python
# Added to existing PurchaseOrder model (Phase 7):
created_by = Column(String(128), nullable=True)
# NULL for POs created before Phase 8 (pre-auth); populated from AuthService.get_current_user().username
```

---

### 4.2 Repository Layer

#### 4.2.1 `UserRepository` (`src/repositories/user_repository.py`)

| Method | Returns | Description |
|---|---|---|
| `get_all(active_only=True)` | `list[User]` | All users ordered by `username ASC` |
| `get_by_id(user_id)` | `User \| None` | Single user by PK |
| `get_by_username(username)` | `User \| None` | Case-insensitive exact match via `LOWER()` |
| `create(username, hashed_password, role, **kwargs)` | `User` | Insert and commit; raises `IntegrityError` on duplicate username |
| `update(user_id, **fields)` | `User \| None` | Partial update; updates `updated_at` |
| `deactivate(user_id)` | `bool` | Sets `active=False`; returns `False` if not found |
| `increment_failed_attempts(user_id)` | `int` | Atomically increments `failed_attempts`; returns new count |
| `reset_failed_attempts(user_id)` | `None` | Sets `failed_attempts = 0` after successful authentication |

---

#### 4.2.2 `AuditEventRepository` (`src/repositories/audit_event_repository.py`)

| Method | Returns | Description |
|---|---|---|
| `create(event_type, actor, entity_type=None, entity_id=None, detail=None)` | `AuditEvent` | Insert and commit; `occurred_at` defaults to `utcnow()` |
| `get_all(limit=200, offset=0)` | `list[AuditEvent]` | All events ordered by `occurred_at DESC` |
| `get_by_event_type(event_type, limit=100)` | `list[AuditEvent]` | Filtered by `event_type`; ordered by `occurred_at DESC` |
| `get_by_actor(username, limit=100)` | `list[AuditEvent]` | Events by a specific actor; ordered by `occurred_at DESC` |
| `get_for_entity(entity_type, entity_id)` | `list[AuditEvent]` | All events referencing a specific entity row |
| `prune_old_events(retention_days)` | `int` | Deletes events where `occurred_at < now() - retention_days`; returns deleted count |

---

#### 4.2.3 `ReportScheduleRepository` (`src/repositories/report_schedule_repository.py`)

| Method | Returns | Description |
|---|---|---|
| `get_all(active_only=False)` | `list[ReportSchedule]` | All schedules ordered by `id ASC` |
| `get_by_id(schedule_id)` | `ReportSchedule \| None` | Single schedule by PK |
| `get_active()` | `list[ReportSchedule]` | All schedules with `active=True`; used at scheduler startup |
| `create(report_type, export_format, cron_expression, output_dir, created_by)` | `ReportSchedule` | Insert and commit |
| `update(schedule_id, **fields)` | `ReportSchedule \| None` | Partial update; validates `export_format` and `report_type` enum values |
| `deactivate(schedule_id)` | `bool` | Sets `active=False`; removes corresponding APScheduler job |
| `record_run(schedule_id, status)` | `ReportSchedule \| None` | Sets `last_run_at = utcnow()`, `last_run_status = status` |

---

### 4.3 Service Layer

#### 4.3.1 `AuthService` (`src/services/auth_service.py`)

| Method | Returns | Description |
|---|---|---|
| `authenticate(username, password)` | `User \| None` | Verifies credentials; enforces lockout; sets session; emits `LOGIN` audit event |
| `logout()` | `None` | Clears `_current_user`; emits `LOGOUT` audit event |
| `get_current_user()` | `User \| None` | Returns module-level `_current_user` (None if not authenticated) |
| `require_role(*roles)` | `None` | Raises `PermissionDeniedError` if `_current_user.role not in roles` |
| `hash_password(plain)` | `str` | Returns bcrypt hash using `passlib.context.CryptContext(schemes=["bcrypt"], rounds=10)` |
| `verify_password(plain, hashed)` | `bool` | Verifies plain text against stored hash |
| `create_default_admin()` | `User` | Creates `username="admin"`, `password="admin123"`, `role=ADMIN`; called on first run when `user` table is empty; logs warning to force password change |
| `change_password(user_id, old_password, new_password)` | `bool` | Verifies old password; updates hash; returns `False` if old password wrong |

**Authentication flow:**

```
authenticate(username, password):
  1. user = UserRepository.get_by_username(username)
     └── If None or active=False → return None (do NOT distinguish; prevents username enumeration)

  2. If user.failed_attempts >= MAX_LOGIN_ATTEMPTS (5):
     └── raise LockedAccountError(f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts.")

  3. If NOT verify_password(password, user.hashed_password):
     ├── UserRepository.increment_failed_attempts(user_id)
     └── return None

  4. UserRepository.reset_failed_attempts(user_id)
  5. UPDATE user.last_login_at = utcnow()
  6. _current_user = user
  7. AuditService.log("LOGIN", actor=username)
  8. return user
```

---

#### 4.3.2 `AuditService` (`src/services/audit_service.py`)

| Method | Returns | Description |
|---|---|---|
| `log(event_type, actor, entity_type=None, entity_id=None, detail=None)` | `AuditEvent` | Serialises `detail` dict to JSON string; calls `AuditEventRepository.create()` |
| `get_recent_events(limit=200)` | `list[dict]` | Serialised recent events for `AuditLogView` |
| `get_events_for_entity(entity_type, entity_id)` | `list[dict]` | Event history for a specific entity row |
| `get_events_by_actor(username)` | `list[dict]` | Activity history for a specific user |
| `prune_old_events()` | `int` | Calls `AuditEventRepository.prune_old_events(AUDIT_RETENTION_DAYS)`; called by weekly APScheduler job |

**Integration points in existing services:**

| Service | Method | Event Type | Detail |
|---|---|---|---|
| `AuthService` | `authenticate()` | `LOGIN` | `{}` |
| `AuthService` | `logout()` | `LOGOUT` | `{}` |
| `PurchaseOrderService` | `submit_po()` | `PO_STATUS_CHANGE` | `{"from": "DRAFT", "to": "SUBMITTED", "po_number": "..."}` |
| `PurchaseOrderService` | `confirm_po()` | `PO_STATUS_CHANGE` | `{"from": "SUBMITTED", "to": "CONFIRMED", "expected_arrival": "..."}` |
| `PurchaseOrderService` | `receive_po()` | `PO_STATUS_CHANGE` | `{"from": "CONFIRMED", "to": "RECEIVED", "actual_qty": N}` |
| `SupplierService` | `create_supplier()` | `SUPPLIER_CREATED` | `{"name": "..."}` |
| `SupplierService` | `deactivate_supplier()` | `SUPPLIER_DEACTIVATED` | `{"name": "..."}` |
| `OptimizationService` | `run_optimization()` | `OPTIMIZATION_RUN` | `{"run_id": N, "product_count": 20}` |
| `SchedulerService` | `_run_scheduled_report()` | `SCHEDULE_RUN` | `{"report_type": "...", "format": "...", "status": "SUCCESS"}` |
| `ImportWizardService` | `import_products()` | `IMPORT_COMPLETED` | `{"import_type": "PRODUCTS", "imported": N, "skipped": M}` |

---

#### 4.3.3 `SettingsService` (`src/services/settings_service.py`)

Settings are persisted in `config/settings.json`. This file — not the database — is the backing store so that `db_path` itself can be configured without a chicken-and-egg problem.

**Default schema (`config/settings.json`):**

```json
{
  "db_path":                "data/logistics.db",
  "log_level":              "INFO",
  "export_dir":             "exports/",
  "theme":                  "dark",
  "language":               "en",
  "audit_retention_days":   365,
  "min_schedule_interval_hours": 1
}
```

| Method | Returns | Description |
|---|---|---|
| `get(key, default=None)` | `Any` | Returns value from in-memory dict; falls back to `default` if key absent |
| `set(key, value)` | `None` | Updates in-memory dict; writes entire dict to `settings.json` |
| `get_all()` | `dict` | Returns a copy of the full settings dict |
| `reset_to_defaults()` | `None` | Overwrites in-memory dict and `settings.json` with `SETTINGS_DEFAULTS` constant |

---

#### 4.3.4 `SchedulerService` (`src/services/scheduler_service.py`)

| Method | Returns | Description |
|---|---|---|
| `start()` | `None` | Instantiates `APScheduler.BackgroundScheduler`; loads all active `ReportSchedule` rows; registers each as a cron job; adds weekly audit-prune job; starts scheduler |
| `stop()` | `None` | Calls `scheduler.shutdown(wait=False)`; called on app exit |
| `create_schedule(report_type, export_format, cron_expression, output_dir)` | `dict` | Validates cron expression and minimum interval; persists `ReportSchedule`; registers APScheduler job |
| `update_schedule(schedule_id, **fields)` | `dict \| None` | Re-validates cron if changed; updates DB row; reschedules APScheduler job |
| `deactivate_schedule(schedule_id)` | `bool` | Sets `active=False`; removes APScheduler job |
| `get_all_schedules()` | `list[dict]` | Serialised schedule list with `next_run_time` from APScheduler |

**Thread-safe UI notification:**

```python
# SchedulerService posts to a module-level queue after each job run:
_update_queue: queue.Queue = queue.Queue()

def _run_scheduled_report(self, schedule_id: int) -> None:
    """Executes in APScheduler background thread — no Tkinter calls allowed."""
    try:
        schedule = self._schedule_repo.get_by_id(schedule_id)
        self._report_runner.generate(
            schedule.report_type, schedule.export_format, schedule.output_dir
        )
        self._schedule_repo.record_run(schedule_id, "SUCCESS")
        AuditService().log("SCHEDULE_RUN", actor="scheduler",
                           entity_type="ReportSchedule", entity_id=schedule_id,
                           detail={"status": "SUCCESS"})
        _update_queue.put({"type": "SCHEDULE_RUN", "schedule_id": schedule_id,
                           "status": "SUCCESS"})
    except Exception as exc:
        self._schedule_repo.record_run(schedule_id, "FAILURE")
        _update_queue.put({"type": "SCHEDULE_RUN", "schedule_id": schedule_id,
                           "status": "FAILURE", "error": str(exc)})
```

`App` polls the queue every 2 seconds via `self.after(2000, self._poll_scheduler_queue)` and refreshes `SettingsView` if it is currently mapped.

**Cron validation:**

```python
def _validate_cron(self, expression: str) -> None:
    """Raises ValueError for invalid syntax or too-frequent schedules."""
    try:
        trigger = CronTrigger.from_crontab(expression)
    except ValueError as exc:
        raise ValueError(f"Invalid cron expression '{expression}': {exc}")

    # Enforce minimum interval: two consecutive fire times must be ≥ 1 hour apart
    now = datetime.utcnow()
    t1 = trigger.get_next_fire_time(None, now)
    t2 = trigger.get_next_fire_time(t1, t1)
    if t2 and (t2 - t1).total_seconds() < MIN_SCHEDULE_INTERVAL_SECONDS:
        raise ValueError(
            f"Schedule interval too short ({(t2 - t1).total_seconds() / 60:.0f} min). "
            f"Minimum is {MIN_SCHEDULE_INTERVAL_SECONDS // 3600} hour(s)."
        )
```

---

#### 4.3.5 `ImportWizardService` (`src/services/import_wizard_service.py`)

| Method | Returns | Description |
|---|---|---|
| `get_import_preview(path, import_type)` | `list[dict]` | Returns first 10 rows of the file as dicts (CSV or Excel auto-detected by extension) |
| `validate_product_file(path)` | `dict` | `{errors: [...], warnings: [...], row_count: N}` — validates required columns, types, and value ranges |
| `validate_demand_file(path)` | `dict` | Validates required columns; cross-checks SKUs against the `Product` table |
| `validate_supplier_file(path)` | `dict` | Validates required columns; checks for duplicate names within the file |
| `import_products(path, overwrite_existing=False)` | `dict` | Commits valid rows; returns `{imported_count, skipped_count, errors}`; emits `IMPORT_COMPLETED` audit event |
| `import_demand_history(path)` | `dict` | Appends demand rows; deduplicates by `(sku, date)`; returns counts and audit event |
| `import_suppliers(path)` | `dict` | Creates `Supplier` rows; skips duplicates by name; returns counts and audit event |

**Column requirements:**

*Products (CSV/Excel):*

| Column | Required | Type | Validation |
|---|---|---|---|
| `sku` | Yes | String | 1–32 chars; no whitespace |
| `name` | Yes | String | 1–128 chars |
| `category` | No | String | max 64 chars; default `""` |
| `abc_class` | No | `A\|B\|C` | default `A` |
| `unit_cost` | No | Float | ≥ 0; default `0.0` |
| `current_stock` | No | Int | ≥ 0; default `0` |

*Demand History (CSV/Excel):*

| Column | Required | Type | Validation |
|---|---|---|---|
| `sku` | Yes | String | Must exist in `Product` table |
| `date` | Yes | Date | ISO 8601 (`YYYY-MM-DD`) |
| `quantity` | Yes | Int | ≥ 0 |

*Suppliers (CSV/Excel):*

| Column | Required | Type | Validation |
|---|---|---|---|
| `name` | Yes | String | 1–128 chars; unique within file |
| `default_lead_time_days` | Yes | Int | ≥ 1 |
| `contact_name` | No | String | max 128 chars |
| `email` | No | String | valid email format |
| `phone` | No | String | max 32 chars |
| `lead_time_std_days` | No | Float | ≥ 0; default `0.0` |

---

### 4.4 RBAC Permission Matrix

| Action | VIEWER | BUYER | ADMIN |
|---|:---:|:---:|:---:|
| View Dashboard / KPIs | ✓ | ✓ | ✓ |
| View Inventory | ✓ | ✓ | ✓ |
| View Forecasts | ✓ | ✓ | ✓ |
| Run Optimisation | ✗ | ✓ | ✓ |
| View Alerts | ✓ | ✓ | ✓ |
| Create PO Draft | ✗ | ✓ | ✓ |
| Submit / Confirm / Receive PO | ✗ | ✓ | ✓ |
| Cancel PO | ✗ | ✓ | ✓ |
| View Suppliers | ✓ | ✓ | ✓ |
| Add / Edit Supplier | ✗ | ✗ | ✓ |
| Deactivate Supplier | ✗ | ✗ | ✓ |
| View Reports | ✓ | ✓ | ✓ |
| Generate Reports | ✗ | ✓ | ✓ |
| View Executive Dashboard | ✓ | ✓ | ✓ |
| Import Data (Wizard) | ✗ | ✗ | ✓ |
| Export / Download Reports | ✗ | ✓ | ✓ |
| Manage Scheduled Reports | ✗ | ✗ | ✓ |
| View Audit Log | ✗ | ✗ | ✓ |
| Manage Users | ✗ | ✗ | ✓ |
| Change Application Settings | ✗ | ✗ | ✓ |

**Enforcement layers:**

1. **UI layer (primary):** buttons, menu items, and navigation entries not permitted by the current role are hidden (`widget.grid_remove()`) or replaced with a padlock icon.
2. **Service layer (defence-in-depth):** `AuthService.require_role()` called at the top of restricted service methods; raises `PermissionDeniedError` if the current user's role is not in the allowed set. This prevents accidental bypasses if the UI layer has a bug.

---

### 4.5 Presentation Layer

#### 4.5.1 `LoginView` (`src/ui/views/login_view.py`)

```
┌──────────────────────────────────────────┐
│                                          │
│         LOGISTICS DSS  v1.0.0            │
│                                          │
│  Username:  [________________________]   │
│  Password:  [________________________]   │
│                                          │
│             [  Log In  ]                 │
│                                          │
│  [!] Invalid username or password.       │
│      (shown only on failed attempt)      │
│                                          │
└──────────────────────────────────────────┘
```

- On first launch (empty `user` table): creates default ADMIN account silently, then displays LoginView with a yellow banner: *"Default admin account created. Username: admin / Password: admin123. Change your password immediately."*
- On successful login: destroys `LoginView`; instantiates and shows the full `App` with sidebar appropriate for the authenticated role.
- On account lockout (5 failed attempts): shows *"Account locked. Contact your administrator."*; Log In button disabled.

---

#### 4.5.2 `SettingsView` (`src/ui/views/settings_view.py`)

```
┌──────────────────────────────────────────────────────────────┐
│  SETTINGS                                                     │
├──────────────────────────────────────────────────────────────┤
│  GENERAL                                                      │
│  Database path:   [data/logistics.db              ] [Browse] │
│  Log level:       [INFO ▼]                                    │
│  Theme:           [Dark ▼]                                    │
│  Language:        [English ▼]                                 │
├──────────────────────────────────────────────────────────────┤
│  REPORTS                                                      │
│  Default export directory: [exports/              ] [Browse] │
├──────────────────────────────────────────────────────────────┤
│  SCHEDULED REPORTS                           (ADMIN only)    │
│  ┌──────────┬────────┬─────────────┬────────┬──────────────┐ │
│  │ Type     │ Format │ Cron        │ Status │ Last Run     │ │
│  ├──────────┼────────┼─────────────┼────────┼──────────────┤ │
│  │ POLICY   │ PDF    │ 0 8 * * 1  │ Active │ Mon 08:00    │ │
│  │ INVENTORY│ EXCEL  │ 0 7 * * *  │ Active │ Today 07:00  │ │
│  └──────────┴────────┴─────────────┴────────┴──────────────┘ │
│  [+ Add Schedule]  [Edit]  [Deactivate]                      │
├──────────────────────────────────────────────────────────────┤
│  USER MANAGEMENT                             (ADMIN only)    │
│  [Manage Users →]                                            │
├──────────────────────────────────────────────────────────────┤
│  [Save Settings]          [Reset to Defaults]                │
└──────────────────────────────────────────────────────────────┘
```

- **Add/Edit Schedule modal (`CTkToplevel`):** Report type dropdown, format dropdown, cron expression field with inline validation feedback, output directory field with Browse button.
- **User management panel (inline, expanded on click):** `DataTable` listing all users with columns: Username, Display Name, Role, Active, Last Login. Action buttons: `[+ Add User]`, `[Edit Role]`, `[Deactivate]`, `[Reset Password]`.
- Theme change applied immediately via `ctk.set_appearance_mode()`; no restart required.

---

#### 4.5.3 `ImportWizardView` (`src/ui/views/import_wizard_view.py`)

Five-step wizard implemented as a `CTkFrame` stack; only the active step frame is visible.

```
Step 1 — Select Import Type
  ┌──────────┐  ┌────────────────┐  ┌──────────┐
  │ Products │  │ Demand History │  │Suppliers │
  └──────────┘  └────────────────┘  └──────────┘
  [Next →]

Step 2 — Select File
  File:  [                                    ] [Browse…]
  Detected format: CSV  |  Rows detected: 22
  [← Back]  [Next →]

Step 3 — Validation & Preview
  ✓ 20 rows valid    ⚠ 2 warnings    ✗ 0 errors
  ┌──────┬──────────────┬─────────────┬──────────┐
  │ SKU  │ Name         │ Unit Cost   │ Category │
  ├──────┼──────────────┼─────────────┼──────────┤
  │ S001 │ Gadget Ultra │ 8.00        │ A        │
  │ ...  │ (first 10)   │             │          │
  └──────┴──────────────┴─────────────┴──────────┘
  [← Back]  [Next →]

Step 4 — Options
  [✓] Skip duplicate records (overwrite_existing = False)
  [ ] Overwrite existing records
  [← Back]  [Next →]

Step 5 — Import
  [  Start Import  ]
  ████████████████░░░░  18 / 20 rows
  ✓ Imported: 18    ⊘ Skipped: 2    ✗ Errors: 0
  [Close]
```

---

#### 4.5.4 `AuditLogView` (`src/ui/views/audit_log_view.py`)

Accessible to ADMIN role only. BUYER or VIEWER navigating to this view sees a centred "Access Denied — Administrator role required." label.

```
┌────────────────────────────────────────────────────────────────┐
│  AUDIT LOG        Filter: [All ▼]    Actor: [______]  [Search] │
├────────────────┬────────────────────┬───────────┬─────────────┤
│  Timestamp     │  Event Type        │  Actor    │  Detail     │
├────────────────┼────────────────────┼───────────┼─────────────┤
│ 2026-02-21 ... │ PO_STATUS_CHANGE   │ gilvan    │ CONFIRMED   │
│ 2026-02-21 ... │ LOGIN              │ gilvan    │             │
│ 2026-02-21 ... │ OPTIMIZATION_RUN   │ gilvan    │ Run #3      │
│ 2026-02-21 ... │ IMPORT_COMPLETED   │ admin     │ 20 products │
│     ...        │                    │           │             │
└────────────────┴────────────────────┴───────────┴─────────────┘
│  Showing 200 most recent events                 [Export CSV]  │
└────────────────────────────────────────────────────────────────┘
```

---

#### 4.5.5 App Extension

Changes to `src/ui/app.py`:

1. **Login gate:** `main.py` no longer calls `App()` directly. Instead, it shows `LoginView(on_success=lambda user: App(current_user=user).mainloop())`.
2. **Current user context:** `App.__init__` receives `current_user: User`; stores as `self.current_user`; passes to all view constructors.
3. **RBAC sidebar:** Navigation buttons shown/hidden based on `current_user.role` at startup. VIEWER: no "Import Data", "Settings", "Audit Log". BUYER: no "Settings", "Audit Log".
4. **New navigation buttons:**
   - **"Settings"** (12th position) — navigates to `SettingsView`; visible to ADMIN only
   - **"Import Data"** (13th position) — navigates to `ImportWizardView`; visible to ADMIN only
   - **"Audit Log"** (14th position) — navigates to `AuditLogView`; visible to ADMIN only
5. **Scheduler startup:** `App.__init__` calls `SchedulerService.start()` after all views are initialised; `SchedulerService.stop()` called on `App.destroy()`.
6. **Queue polling:** `self.after(2000, self._poll_scheduler_queue)` started in `App.__init__`.

---

## 5. Data Flow

### 5.1 Authentication and Login Flow

```
Application starts (main.py)
    │
    ▼
LoginView shown (CTk root window)
    ├── Check: UserRepository.get_all() == []?
    │         → AuthService.create_default_admin()
    │         → Show "default admin created" banner
    │
    ▼ (user enters credentials and clicks [Log In])
AuthService.authenticate(username, password)
    ├── get_by_username()  →  User found
    ├── failed_attempts < MAX_LOGIN_ATTEMPTS (5)?  →  yes
    ├── verify_password(password, hashed_password)  →  True
    ├── reset_failed_attempts()
    ├── update last_login_at
    ├── _current_user = user
    ├── AuditService.log("LOGIN", actor=username)
    └── return User
            │
            ▼
LoginView.on_success(user) callback
    ├── LoginView.destroy()
    └── App(current_user=user)
            ├── Build sidebar (role-filtered)
            ├── SchedulerService.start()
            └── self.after(2000, _poll_scheduler_queue)
```

### 5.2 Scheduled Report Execution Flow

```
SchedulerService.start()
    ├── Load all ReportSchedule rows where active=True
    ├── For each schedule:
    │       scheduler.add_job(
    │           func=_run_scheduled_report,
    │           trigger=CronTrigger.from_crontab(schedule.cron_expression),
    │           args=[schedule.id],
    │       )
    └── scheduler.add_job(audit_service.prune_old_events,
                          CronTrigger(day_of_week="sun", hour=2))
                                │
               (cron trigger fires at scheduled time)
                                │
                                ▼
         APScheduler background thread calls:
         SchedulerService._run_scheduled_report(schedule_id)
             ├── ReportRunner.generate(report_type, export_format, output_dir)
             ├── ReportScheduleRepository.record_run(schedule_id, "SUCCESS")
             ├── AuditService.log("SCHEDULE_RUN", ...)
             └── _update_queue.put({"type": "SCHEDULE_RUN", ...})
                                │
            (main thread polls queue every 2 seconds)
                                │
                                ▼
         App._poll_scheduler_queue()
             └── If SettingsView is mapped:
                     SettingsView.refresh_schedule_list()
                     → Last Run column updated to "Today HH:MM ✓"
```

### 5.3 Data Import Flow (Products)

```
User (ADMIN) navigates to Import Data
    │
    ▼
ImportWizardView — Step 1: selects "Products"
    │
    ▼
Step 2: browses to "products.csv"
    ├── ImportWizardService.get_import_preview("products.csv", "PRODUCTS")
    └── Shows file info: format=CSV, rows=22

    │
    ▼
Step 3: Validation & Preview
    ├── ImportWizardService.validate_product_file("products.csv")
    │       ├── Parse CSV with pandas
    │       ├── Check required columns (sku, name)
    │       ├── Validate each row: unit_cost ≥ 0, abc_class in {A,B,C}, etc.
    │       └── Return {errors: [], warnings: ["Row 14: abc_class blank, defaulting to A"], row_count: 22}
    └── Preview DataTable shows first 10 rows

    │
    ▼
Step 4: Options — user selects "Skip duplicate records"

    │
    ▼
Step 5: Start Import
    ├── ImportWizardService.import_products("products.csv", overwrite_existing=False)
    │       ├── Load existing SKUs from Product table into set
    │       ├── For each valid row:
    │       │       ├── If SKU in existing_skus → skipped_count += 1
    │       │       └── Else → ProductRepository.create(...); imported_count += 1
    │       ├── session.commit()
    │       ├── AuditService.log("IMPORT_COMPLETED", actor=current_user.username,
    │       │       detail={"import_type": "PRODUCTS", "imported": 20, "skipped": 2})
    │       └── Return {imported_count: 20, skipped_count: 2, errors: []}
    └── Progress bar completes; results shown: "✓ Imported: 20    ⊘ Skipped: 2"
```

---

## 6. Packaging

### 6.1 PyInstaller Spec (`packaging/logistics_dss.spec`)

```python
# logistics_dss.spec
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=[],
    datas=[
        ("../config/",   "config/"),
        ("../assets/",   "assets/"),
        # CustomTkinter theme assets must be bundled explicitly:
        (str(Path(sys.prefix) / "lib/python3.12/site-packages/customtkinter"),
         "customtkinter"),
    ],
    hiddenimports=[
        "customtkinter",
        "sqlalchemy.dialects.sqlite",
        "apscheduler.schedulers.background",
        "apscheduler.triggers.cron",
        "passlib.handlers.bcrypt",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "matplotlib.tests"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name="LogisticsDSS",
    icon="../assets/icon.ico",
    console=False,
    onefile=True,
)

# macOS .app bundle
app = BUNDLE(
    exe,
    name="LogisticsDSS.app",
    icon="../assets/icon.icns",
    bundle_identifier="com.gilvan.logistics-dss",
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
)
```

### 6.2 `pyproject.toml` (`packaging/pyproject.toml`)

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "logistics-dss"
version = "1.0.0"
description = "Logistics Decision Support System — desktop inventory management application"
authors = [{ name = "Gilvan de Azevedo" }]
requires-python = ">=3.12"
license = { text = "Proprietary" }
dependencies = [
    "customtkinter>=5.2",
    "sqlalchemy>=2.0",
    "pandas>=2.1",
    "numpy>=1.26",
    "statsmodels>=0.14",
    "reportlab>=4.0",
    "openpyxl>=3.1",
    "passlib[bcrypt]>=1.7",
    "apscheduler>=3.10",
    "matplotlib>=3.8",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*", "config*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--tb=short -q"
```

---

## 7. New Configuration Constants (`config/constants.py`)

| Constant | Default | Description |
|---|---|---|
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed login attempts before account lockout |
| `ROLE_ADMIN` | `"ADMIN"` | Full system access including user management and settings |
| `ROLE_BUYER` | `"BUYER"` | Full PO workflow access; no system configuration |
| `ROLE_VIEWER` | `"VIEWER"` | Read-only access across all views |
| `ALL_ROLES` | `("ADMIN", "BUYER", "VIEWER")` | All valid role values |
| `AUDIT_RETENTION_DAYS` | `365` | Events older than this are pruned by the weekly APScheduler job |
| `AUDIT_PRUNE_CRON` | `"0 2 * * 0"` | Weekly Sunday 02:00 UTC audit prune cron expression |
| `MIN_SCHEDULE_INTERVAL_SECONDS` | `3600` | Minimum permitted interval between scheduled report runs (1 hour) |
| `BCRYPT_ROUNDS` | `10` | bcrypt work factor; balances security and login latency |
| `DEFAULT_ADMIN_USERNAME` | `"admin"` | Auto-created admin username on first run |
| `DEFAULT_ADMIN_PASSWORD` | `"admin123"` | Plaintext default password; hashed on creation; must be changed |
| `SETTINGS_FILE_PATH` | `"config/settings.json"` | Path to runtime settings file |
| `SETTINGS_DEFAULTS` | `{...}` | Full default settings dict (db_path, log_level, theme, language, …) |
| `IMPORT_TYPE_PRODUCTS` | `"PRODUCTS"` | Import wizard: product master |
| `IMPORT_TYPE_DEMAND` | `"DEMAND"` | Import wizard: historical demand |
| `IMPORT_TYPE_SUPPLIERS` | `"SUPPLIERS"` | Import wizard: supplier master |
| `SCHEDULER_QUEUE_POLL_MS` | `2000` | Milliseconds between main-thread checks of the scheduler notification queue |

---

## 8. Technology Stack (Phase 8 Additions)

| Capability | Package | Version | Usage |
|---|---|---|---|
| Password hashing | `passlib[bcrypt]` | ≥ 1.7.4 | `CryptContext(schemes=["bcrypt"])` in `AuthService`; bcrypt rounds=10 |
| Job scheduling | `apscheduler` | ≥ 3.10 | `BackgroundScheduler` + `CronTrigger` in `SchedulerService`; background thread, no UI dependency |
| Desktop packaging | `pyinstaller` | ≥ 6.3 | Single-file `.exe` / `.app` build via `packaging/logistics_dss.spec` |

All other Phase 8 functionality uses packages already present from Phases 1–7:

| Capability | Package (already installed) | Usage |
|---|---|---|
| ORM + DB | SQLAlchemy + SQLite | User, ReportSchedule, AuditEvent models |
| Date arithmetic | Python `datetime` (stdlib) | `audit_event.occurred_at`, `last_login_at` |
| JSON I/O | Python `json` (stdlib) | `SettingsService` settings.json read/write; `AuditEvent.detail` serialisation |
| Thread safety | Python `queue` (stdlib) | Scheduler → main thread notification queue |
| CSV/Excel import | `pandas` + `openpyxl` (Phase 1/6) | `ImportWizardService` file parsing |
| UI | CustomTkinter | LoginView, SettingsView, ImportWizardView, AuditLogView |
| Reports | `reportlab` + `openpyxl` (Phase 6) | `ReportRunner.generate()` called by `SchedulerService` |

**Updated `requirements.txt`:** 2 new entries — `passlib[bcrypt]>=1.7.4` and `apscheduler>=3.10`.

---

## 9. Implementation Tasks

### 9.1 Constants, ORM & Dependencies (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T8-01 | Add Phase 8 constants and `SETTINGS_DEFAULTS` to `config/constants.py` | `config/constants.py` | 15 min |
| T8-02 | Add `User`, `ReportSchedule`, `AuditEvent` ORM models; add `created_by` to `PurchaseOrder` | `src/database/models.py` | 45 min |
| T8-03 | Database migration: 3 new tables + `PurchaseOrder.created_by` column | Bash / SQLAlchemy `create_all()` | 10 min |
| T8-04 | Add `passlib[bcrypt]` and `apscheduler` to `requirements.txt`; install in venv | `requirements.txt` | 5 min |

### 9.2 Repository Layer (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T8-05 | Implement `UserRepository` (8 methods) | `src/repositories/user_repository.py` | 1 h |
| T8-06 | Implement `AuditEventRepository` (6 methods) | `src/repositories/audit_event_repository.py` | 45 min |
| T8-07 | Implement `ReportScheduleRepository` (7 methods) | `src/repositories/report_schedule_repository.py` | 1 h |

### 9.3 Service Layer (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T8-08 | Implement `AuthService` (8 methods + session state + bcrypt + lockout) | `src/services/auth_service.py` | 3 h |
| T8-09 | Implement `AuditService` (5 methods + JSON detail serialisation) | `src/services/audit_service.py` | 1 h |
| T8-10 | Implement `SettingsService` (4 methods + `settings.json` I/O) | `src/services/settings_service.py` | 1.5 h |
| T8-11 | Implement `SchedulerService` (6 methods + APScheduler + cron validation + notification queue) | `src/services/scheduler_service.py` | 3 h |
| T8-12 | Implement `ImportWizardService` (7 methods + validation + preview for 3 data types) | `src/services/import_wizard_service.py` | 3.5 h |
| T8-13 | Extend `PurchaseOrderService`, `SupplierService`, `OptimizationService` with `AuditService` calls and `require_role()` checks | 3 existing service files | 2 h |
| T8-14 | Extend `PurchaseOrderService.create_po()` to populate `created_by` from `AuthService.get_current_user()` | `src/services/purchase_order_service.py` | 20 min |

### 9.4 UI Layer (Priority: Medium)

| # | Task | Module | Effort |
|---|---|---|---|
| T8-15 | Implement `LoginView` (login form + startup gate + first-run banner) | `src/ui/views/login_view.py` | 3 h |
| T8-16 | Implement `SettingsView` (general settings + scheduled reports panel + user management table) | `src/ui/views/settings_view.py` | 4 h |
| T8-17 | Implement `ImportWizardView` (five-step wizard: type → file → validate → options → execute) | `src/ui/views/import_wizard_view.py` | 5 h |
| T8-18 | Implement `AuditLogView` (paginated audit table + filter + ADMIN gate) | `src/ui/views/audit_log_view.py` | 2 h |
| T8-19 | Extend `App`: login gate, `current_user` injection, new nav buttons, scheduler startup, queue polling | `src/ui/app.py` | 2 h |
| T8-20 | Apply RBAC across all existing views (hide/disable buttons based on role) | 6 existing view files | 3 h |

### 9.5 Packaging (Priority: Medium)

| # | Task | Module | Effort |
|---|---|---|---|
| T8-21 | Create `packaging/logistics_dss.spec` (PyInstaller spec with correct `datas`, `hiddenimports`) | `packaging/logistics_dss.spec` | 2 h |
| T8-22 | Create `packaging/pyproject.toml` (pip-installable distribution config) | `packaging/pyproject.toml` | 45 min |
| T8-23 | Run PyInstaller build on macOS; smoke-test resulting `.app` (login → full PO workflow) | Bash | 1.5 h |

### 9.6 Testing (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T8-24 | Write `tests/test_user_repository.py` (7 tests) | `tests/test_user_repository.py` | 1.5 h |
| T8-25 | Write `tests/test_audit_event_repository.py` (6 tests) | `tests/test_audit_event_repository.py` | 1 h |
| T8-26 | Write `tests/test_report_schedule_repository.py` (7 tests) | `tests/test_report_schedule_repository.py` | 1.5 h |
| T8-27 | Write `tests/test_auth_service.py` (9 tests) | `tests/test_auth_service.py` | 2 h |
| T8-28 | Write `tests/test_settings_service.py` (6 tests) | `tests/test_settings_service.py` | 1 h |
| T8-29 | Write `tests/test_scheduler_service.py` (7 tests) | `tests/test_scheduler_service.py` | 1.5 h |
| T8-30 | Write `tests/test_import_wizard.py` (8 tests) | `tests/test_import_wizard.py` | 2 h |
| T8-31 | Write `tests/test_rbac_enforcement.py` (6 tests) | `tests/test_rbac_enforcement.py` | 1.5 h |

**Total estimated effort: 50–65 hours**

---

## 10. Implementation Order

```
Step 1: Constants, ORM & Dependencies
  ├── T8-01: Phase 8 constants
  ├── T8-02: ORM models (User, ReportSchedule, AuditEvent) + PurchaseOrder.created_by
  ├── T8-03: Database migration
  └── T8-04: Install passlib[bcrypt] + apscheduler

Step 2: Repository Layer
  ├── T8-05: UserRepository
  ├── T8-06: AuditEventRepository
  └── T8-07: ReportScheduleRepository

Step 3: Service Layer (bottom-up)
  ├── T8-09: AuditService       (depends on T8-06)
  ├── T8-08: AuthService        (depends on T8-05 + T8-09)
  ├── T8-10: SettingsService    (independent — file-backed, no DB)
  ├── T8-11: SchedulerService   (depends on T8-07 + T8-09)
  ├── T8-12: ImportWizardService (depends on T8-09; reads Product + Supplier tables)
  ├── T8-13: Extend existing services with AuditService + RBAC (depends on T8-08 + T8-09)
  └── T8-14: PurchaseOrderService.created_by (depends on T8-08)

Step 4: Testing (immediately after each component)
  ├── T8-24: UserRepository tests          ← after T8-05
  ├── T8-25: AuditEventRepository tests    ← after T8-06
  ├── T8-26: ReportScheduleRepository tests ← after T8-07
  ├── T8-27: AuthService tests             ← after T8-08
  ├── T8-28: SettingsService tests         ← after T8-10
  ├── T8-29: SchedulerService tests        ← after T8-11
  ├── T8-30: ImportWizardService tests     ← after T8-12
  └── T8-31: RBAC enforcement tests        ← after T8-13

Step 5: UI Layer (after service layer is fully tested)
  ├── T8-15: LoginView
  ├── T8-16: SettingsView
  ├── T8-17: ImportWizardView
  ├── T8-18: AuditLogView
  ├── T8-19: App extension (login gate + scheduler + queue polling)
  └── T8-20: RBAC across existing views

Step 6: Packaging (after full app is functional)
  ├── T8-21: PyInstaller spec
  ├── T8-22: pyproject.toml
  └── T8-23: Build + smoke test
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| APScheduler background thread calls Tkinter widgets directly, causing `RuntimeError: main thread is not in main loop` | High | High | Strictly enforced: `_run_scheduled_report()` may never call any Tkinter method. All UI updates routed through `_update_queue`; main thread polls via `after()` |
| PyInstaller fails to bundle CustomTkinter theme assets (`*.json` files not collected automatically) | High | Medium | Explicit `datas` entry in `.spec` for the full `customtkinter` package directory; verified in T8-23 smoke test |
| bcrypt verification adds 200–500 ms login latency on low-end hardware (bcrypt rounds=12 default) | Medium | Medium | `BCRYPT_ROUNDS = 10` constant; acceptable 80–150 ms on typical hardware; documented in settings |
| Default admin password `"admin123"` left unchanged in a deployed instance | High | Medium | Force-change banner on every login until password is changed; `AuthService.authenticate()` sets a `must_change_password` flag if credentials match defaults |
| `ImportWizardService.import_products(overwrite_existing=True)` irreversibly overwrites production data | High | Low | Step 4 confirmation checkbox with explicit label *"I understand this will overwrite existing records"*; `AuditEvent` logged immediately; recommend database export before import (shown as wizard warning) |
| `settings.json` `db_path` changed to non-existent path → app fails to connect on next launch | High | Low | `SettingsService.set("db_path", ...)` validates path exists and is writable before persisting; reverts to previous value on failure with an error toast |
| `AuditEvent` table grows unboundedly at high usage (every PO status change writes a row) | Medium | Medium | `AUDIT_RETENTION_DAYS = 365`; weekly prune job removes old events; `AuditLogView` shows only the most recent 200 rows by default |
| `SchedulerService.start()` called before `App` finishes initialising views → queue posted before `after()` loop begins | Medium | Low | `start()` called at end of `App.__init__()` after all view construction; first APScheduler job fires no earlier than its cron trigger; queue drains on first `after()` poll |
| User.failed_attempts counter not persisted to DB before app crash → attack resets counter by restarting app | Medium | Low | `failed_attempts` is a DB column (not in-memory); increment is committed immediately after each failed attempt via `session.commit()` |
| `ImportWizardService.validate_demand_file()` cross-checks SKUs against the live `Product` table: if validation runs before an earlier import step is committed, SKUs may appear absent | Low | Low | Import steps are always independent wizard sessions; demand import wizard shows a warning if product table has fewer than 5 rows |

---

## 12. Testing Strategy

### 12.1 User Repository Tests (`tests/test_user_repository.py`)

| Test | Validates |
|---|---|
| `test_create_user_basic` | `create()` inserts row; `get_by_id()` returns it with correct `username` and `role` |
| `test_create_user_duplicate_username_raises` | Second `create()` with same username raises `IntegrityError` |
| `test_get_by_username_case_insensitive` | `get_by_username("GILVAN")` finds user with `username="gilvan"` |
| `test_deactivate_user` | `deactivate()` sets `active=False`; row still returned by `get_by_id()` |
| `test_increment_failed_attempts` | Three calls return 1, 2, 3; value persisted in DB |
| `test_reset_failed_attempts` | After 3 increments, `reset_failed_attempts()` sets `failed_attempts=0` |
| `test_get_all_active_only` | `get_all(active_only=True)` excludes deactivated users |

### 12.2 Audit Event Repository Tests (`tests/test_audit_event_repository.py`)

| Test | Validates |
|---|---|
| `test_create_audit_event` | `create()` inserts row with correct `event_type`, `actor`, and non-null `occurred_at` |
| `test_get_by_event_type_filters` | `get_by_event_type("LOGIN")` returns only `LOGIN` events |
| `test_get_for_entity` | `get_for_entity("PurchaseOrder", 1)` returns all events referencing that entity |
| `test_get_by_actor` | `get_by_actor("gilvan")` excludes events by other actors |
| `test_prune_old_events_count` | Inserting 5 events (3 old, 2 recent): `prune_old_events(30)` deletes 3; returns `3` |
| `test_get_all_ordered_desc` | `get_all()` returns events with most recent `occurred_at` first |

### 12.3 Report Schedule Repository Tests (`tests/test_report_schedule_repository.py`)

| Test | Validates |
|---|---|
| `test_create_schedule` | `create()` inserts row; `get_by_id()` returns with correct `cron_expression` and `active=True` |
| `test_get_all_active_only` | `get_all(active_only=True)` excludes deactivated schedules |
| `test_deactivate_schedule` | `deactivate()` sets `active=False`; schedule absent from `get_active()` |
| `test_record_run_success` | `record_run(schedule_id, "SUCCESS")` sets `last_run_at` to non-null datetime |
| `test_record_run_failure` | `record_run(schedule_id, "FAILURE")` sets `last_run_status="FAILURE"` |
| `test_update_schedule_cron` | `update(schedule_id, cron_expression="0 9 * * *")` persists new expression |
| `test_get_all_returns_all_statuses` | `get_all(active_only=False)` returns both active and inactive schedules |

### 12.4 Auth Service Tests (`tests/test_auth_service.py`)

| Test | Validates |
|---|---|
| `test_authenticate_valid_credentials` | Returns `User` object; `_current_user` set; `last_login_at` updated; `LOGIN` audit event created |
| `test_authenticate_invalid_password` | Returns `None`; `failed_attempts` incremented |
| `test_authenticate_unknown_username` | Returns `None`; no exception raised (prevents username enumeration) |
| `test_authenticate_inactive_user` | Returns `None` even with correct password |
| `test_lockout_after_max_attempts` | 5 failed attempts increment counter; 6th call raises `LockedAccountError` |
| `test_reset_failed_on_success` | 3 failed attempts then 1 successful login → `failed_attempts=0` |
| `test_logout_clears_session` | `logout()` sets `_current_user=None`; `get_current_user()` returns `None`; `LOGOUT` audit event created |
| `test_hash_and_verify_password` | `hash_password("secret")` returns bcrypt string; `verify_password("secret", hash)` is `True`; `verify_password("wrong", hash)` is `False` |
| `test_change_password_wrong_old` | `change_password(user_id, "wrong_old", "new")` returns `False`; hash unchanged |

### 12.5 Settings Service Tests (`tests/test_settings_service.py`)

| Test | Validates |
|---|---|
| `test_get_default_log_level` | `settings.json` absent → `get("log_level", "INFO")` returns `"INFO"` |
| `test_set_and_get` | `set("theme", "light")`; `get("theme")` returns `"light"` |
| `test_set_persists_to_file` | After `set()`, reading `settings.json` directly confirms the value was written |
| `test_get_all_returns_all_default_keys` | `get_all()` dict contains all `SETTINGS_DEFAULTS` keys |
| `test_reset_to_defaults` | After `set("theme", "light")`, `reset_to_defaults()` → `get("theme")` returns `"dark"` |
| `test_invalid_key_returns_default` | `get("nonexistent", "fallback")` returns `"fallback"` without error |

### 12.6 Scheduler Service Tests (`tests/test_scheduler_service.py`)

| Test | Validates |
|---|---|
| `test_create_schedule_persists` | `create_schedule()` creates `ReportSchedule` row; `get_all_schedules()` includes it |
| `test_deactivate_schedule` | `deactivate_schedule()` sets `active=False`; job removed from APScheduler job list |
| `test_invalid_cron_raises` | `create_schedule(cron_expression="not-a-cron")` raises `ValueError` |
| `test_too_frequent_cron_raises` | `cron_expression="*/30 * * * *"` (30-min interval) raises `ValueError` |
| `test_run_scheduled_report_calls_runner` | `_run_scheduled_report()` with mocked `ReportRunner` verifies `generate()` called once with correct arguments |
| `test_run_records_success_status` | After `_run_scheduled_report()` with mock success: `record_run()` called with `"SUCCESS"` |
| `test_run_records_failure_on_exception` | `ReportRunner.generate()` raises `IOError` → `record_run()` called with `"FAILURE"`; exception is swallowed (not propagated) |

### 12.7 Import Wizard Tests (`tests/test_import_wizard.py`)

| Test | Validates |
|---|---|
| `test_validate_product_csv_valid` | 5-row valid CSV → `{errors: [], warnings: [], row_count: 5}` |
| `test_validate_product_csv_missing_required_column` | CSV without `sku` column → `errors` contains `"Required column 'sku' not found"` |
| `test_validate_product_csv_invalid_unit_cost` | Row with `unit_cost=-5` → `errors` contains `"Row 2: unit_cost must be ≥ 0"` |
| `test_import_products_inserts_rows` | 5-row valid CSV → 5 `Product` rows in DB; `imported_count=5`, `skipped_count=0` |
| `test_import_products_skip_duplicates` | CSV with 2 new + 1 existing SKU (`overwrite_existing=False`) → `imported=2`, `skipped=1` |
| `test_import_products_overwrite_duplicates` | CSV with 1 existing SKU (`overwrite_existing=True`) → product `name` updated; `imported=1`, `skipped=0` |
| `test_import_demand_unknown_sku_raises` | Demand CSV referencing `"SKU999"` (not in `Product` table) → `ImportValidationError` raised during validation |
| `test_import_logs_audit_event` | After `import_products()` → `AuditEvent` row exists with `event_type="IMPORT_COMPLETED"` and correct `detail` JSON |

### 12.8 RBAC Enforcement Tests (`tests/test_rbac_enforcement.py`)

| Test | Validates |
|---|---|
| `test_viewer_cannot_create_po` | `PurchaseOrderService.create_po()` with VIEWER `_current_user` → raises `PermissionDeniedError` |
| `test_buyer_cannot_deactivate_supplier` | `SupplierService.deactivate_supplier()` with BUYER session → raises `PermissionDeniedError` |
| `test_admin_can_deactivate_supplier` | `SupplierService.deactivate_supplier()` with ADMIN session → succeeds (no exception) |
| `test_viewer_cannot_run_optimization` | `OptimizationService.run_optimization()` with VIEWER session → raises `PermissionDeniedError` |
| `test_buyer_can_submit_po` | `PurchaseOrderService.submit_po()` with BUYER session → succeeds |
| `test_admin_has_full_access` | ADMIN session: `run_optimization()`, `create_po()`, `deactivate_supplier()` all succeed without exception |

---

## 13. Non-Functional Requirements (Phase 8)

| Requirement | Target | Validation Method |
|---|---|---|
| Login authentication response time | < 1 s (including bcrypt verify) | Timed in `test_auth_service.py::test_authenticate_valid_credentials`; `BCRYPT_ROUNDS=10` |
| Import of 10,000-row CSV (products) | < 30 s | Timed with 10 k-row fixture in `test_import_wizard.py` |
| Scheduled report execution (POLICY PDF) | < 60 s | Timed in `test_scheduler_service.py` with `ReportRunner` on development database |
| `AuditService.log()` write latency | < 50 ms | Synchronous DB write; confirmed by time assertions in `test_audit_event_repository.py` |
| PyInstaller binary startup time | < 5 s | Measured on macOS M1; timed from launch to `LoginView` display in T8-23 smoke test |
| PyInstaller binary size | < 200 MB | Measured after `--onefile` build; noted in T8-23 output |
| Settings load on startup | < 10 ms | File read + JSON parse; confirmed by `test_settings_service.py::test_get_all_returns_all_default_keys` |
| Audit log view (200 rows) | < 1 s | Background thread load with `DataTable` pagination |
| Non-GUI test coverage | ≥ 90% | `pytest --cov=src --ignore=src/ui` |
| Account lockout enforcement | After exactly 5 failed attempts | Verified in `test_auth_service.py::test_lockout_after_max_attempts` |
| Scheduler notification latency (background → UI) | ≤ `SCHEDULER_QUEUE_POLL_MS` (2 s) | Architectural guarantee; queue polled every 2 s by `App.after()` |

---

## 14. Phase 8 Exit Criteria

- [ ] `user`, `report_schedule`, `audit_event` tables created; `purchase_order.created_by` column added; migration verified via `test_database.py` extension
- [ ] `AuthService.authenticate()` returns `User` on valid credentials and `None` on invalid credentials without raising an exception (`test_authenticate_valid_credentials`, `test_authenticate_invalid_password`)
- [ ] `AuthService` raises `LockedAccountError` after `MAX_LOGIN_ATTEMPTS` (5) consecutive failed attempts (`test_lockout_after_max_attempts`)
- [ ] `AuditService.log("LOGIN", ...)` creates an `AuditEvent` row after every successful login (`test_authenticate_valid_credentials`)
- [ ] `SchedulerService.create_schedule()` persists a `ReportSchedule` row with `active=True`; invalid cron expression raises `ValueError` (`test_create_schedule_persists`, `test_invalid_cron_raises`)
- [ ] `SchedulerService._run_scheduled_report()` calls `ReportRunner.generate()` once with correct arguments; records `"SUCCESS"` status on completion and `"FAILURE"` on exception (`test_run_scheduled_report_calls_runner`, `test_run_records_failure_on_exception`)
- [ ] `ImportWizardService.validate_product_file()` returns errors for invalid rows; `import_products()` inserts valid rows, skips duplicates when `overwrite_existing=False`, and emits `IMPORT_COMPLETED` audit event (`test_import_products_inserts_rows`, `test_import_logs_audit_event`)
- [ ] `ImportWizardService.validate_demand_file()` raises `ImportValidationError` when a SKU does not exist in the `Product` table (`test_import_demand_unknown_sku_raises`)
- [ ] RBAC enforcement: VIEWER cannot create PO; BUYER cannot deactivate supplier; ADMIN has full access (`test_rbac_enforcement.py` — all 6 tests pass)
- [ ] `LoginView` renders without exception; successful login shows main `App` window; failed login shows error label; account locked after 5 attempts (manual smoke test)
- [ ] `SettingsView` renders without exception; saving settings updates `settings.json`; theme change applied without restart (manual smoke test)
- [ ] `ImportWizardView` completes a five-step product import with validation preview; results shown in step 5 (manual smoke test)
- [ ] `AuditLogView` renders without exception for ADMIN; BUYER navigation to the view shows "Access Denied" label (manual smoke test)
- [ ] PyInstaller `.app` launches on macOS; `LoginView` shown; full PO workflow (login → DRAFT → SUBMITTED → CONFIRMED → RECEIVED) completes without error (T8-23 packaging smoke test)
- [ ] All 56 new Phase 8 tests pass; total test count = 370; 0 regressions in Phase 1–7 tests
- [ ] Non-GUI test coverage ≥ 90%

---

## 15. Project Completion

Phase 8 is the final phase of the Logistics DSS. Upon completion, the system will be:

- **Analytically complete:** demand forecasting (Phase 4), ABC/XYZ classification (Phase 3), inventory policy optimisation with lead-time-variance safety stock (Phases 5 + 7)
- **Operationally complete:** full purchase order lifecycle with supplier reliability scoring (Phase 7)
- **Reportable:** PDF and Excel exports across four report types with scheduled generation (Phases 6 + 8)
- **Secure:** bcrypt-authenticated users with role-based access control and audit trail (Phase 8)
- **Data-importable:** CSV/Excel bulk import for products, demand history, and supplier master (Phase 8)
- **Deployable:** standalone desktop executable for Windows and macOS; pip-installable package (Phase 8)
- **Fully tested:** 370 passing tests; ≥ 90% non-GUI coverage; ~22,000 lines of source + tests

**Post-launch activities (outside the 8-phase development scope):**

1. **Multilingual UI:** locale files for Portuguese (PT-BR) and Spanish (ES) — i18n string extraction infrastructure is in place via `config/constants.py`; translation files to be created
2. **ERP database connector:** Phase 8 lays the import wizard foundation; a connector would bypass CSV and query an ERP database (SAP, Oracle, Dynamics) directly via a configurable connection string
3. **Multi-location inventory:** a `Location` ORM model and location-filtered views for distribution centres or warehouses
4. **Cloud backup:** scheduled SFTP or S3 upload of the SQLite database file, triggered by the Phase 8 `APScheduler` infrastructure
5. **Read-only mobile companion:** a lightweight web API layer (FastAPI) serving Phase 8's `KPIService` and `ReportService` data to an executive mobile dashboard

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-02-21 | Initial Phase 8 implementation plan |

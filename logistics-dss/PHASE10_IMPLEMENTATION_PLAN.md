# Logistics DSS - Phase 10 Implementation Plan
# ERP Database Connectors & Multi-Location Inventory

**Project:** Logistics Decision Support System
**Phase:** 10 — ERP Database Connectors & Multi-Location Inventory
**Author:** Gilvan de Azevedo
**Date:** 2026-02-26
**Status:** Not Started
**Depends on:** Phase 9 (Multilingual UI) — functionally complete

---

## 1. Phase 10 Objective

Phase 10 delivers two major capability extensions that together position the Logistics DSS as an enterprise-ready system capable of integrating with external data sources and managing inventory across a distributed warehouse network.

**ERP Database Connectors:**
The Phase 8 Import Wizard currently accepts only CSV and Excel files browsed from the local filesystem. Phase 10 introduces a pluggable `DataConnector` framework — an abstract base class with four concrete implementations: `PostgreSQLConnector`, `MySQLConnector`, `SQLiteConnector` (external file, not the app's own database), and `GenericODBCConnector`. A `ConnectionProfile` ORM model stores named connection configurations (host, port, database, credentials) with Fernet-encrypted passwords. A `ConnectionService` provides CRUD operations, a `test_connection()` factory, and a `get_connector()` method that instantiates the correct `DataConnector` subclass from a stored profile.

The `SettingsView` gains a new **Connections** tab listing all saved connection profiles; ADMIN users can add, edit, delete, and test connections. The `ImportWizardView` Step 1 gains a **Source Type** selector — "Browse File" (existing path) or "Database Connection" (new path). When the database path is chosen, Step 1b presents a dropdown of saved active connections; Step 2 becomes a table/view picker populated by `DataConnector.list_tables()`.

**Multi-Location Inventory:**
The current system treats inventory as a single, location-agnostic pool. Phase 10 introduces a three-model location layer: `Location` (warehouse, store, or DC), `ProductLocation` (per-product stock at each location), and `StockTransfer` (movement of goods between locations with a DRAFT → IN_TRANSIT → RECEIVED lifecycle). `LocationService` and `StockTransferService` encapsulate the business logic; atomic stock movements use SQLAlchemy's session-scoped transactions to guarantee consistency under concurrent access.

Two new views are added: `LocationsView` (CRUD for location master data, with a per-location stock summary table) and `StockTransferView` (create drafts, dispatch, receive, and cancel transfers). All existing inventory-facing views — `InventoryView`, `DashboardView`, `AlertsView`, and `ExecutiveView` — gain a **Location** filter `CTkOptionMenu` that defaults to "All Locations" and can be narrowed to any single location.

**Deliverables:**
- `src/connectors/` package: `DataConnector` ABC, `CSVConnector`, `PostgreSQLConnector`, `MySQLConnector`, `SQLiteConnector`, `GenericODBCConnector`
- `ConnectionProfile` ORM model + `ConnectionProfileRepository`
- `ConnectionService`: profile CRUD, `test_connection()`, `get_connector()` factory, Fernet password encryption
- `SettingsView` Connections tab: profile list, add/edit modal, test-connection button
- `ImportWizardView` Step 1 source type selector + database import path (Steps 1b, 2)
- `Location` ORM model + `LocationRepository`
- `ProductLocation` ORM model + `ProductLocationRepository`
- `StockTransfer` ORM model + `StockTransferRepository`
- `LocationService`: CRUD + `get_stock_by_location()` + atomic `move_stock()`
- `StockTransferService`: `create_draft()`, `dispatch()`, `receive()`, `cancel()` with full audit trail
- `LocationsView`: location CRUD + per-location stock summary table
- `StockTransferView`: transfer pipeline with create/dispatch/receive/cancel workflow
- `InventoryView`, `DashboardView`, `AlertsView`, `ExecutiveView`: location filter `CTkOptionMenu`
- `App` navigation: `LocationsView` and `StockTransferView` added to sidebar
- All new strings (~80) added to EN/PT-BR/ES locale catalogs; `.mo` files recompiled
- Updated `packaging/logistics_dss.spec` with connector dependencies
- Full test suite (45 new tests): connector framework, connection service, location service, stock transfer service, multi-location inventory queries

---

## 2. Phase 9 Dependencies (Available)

Phase 10 builds directly on the following Phase 9 (and prior) components:

| Component | Module | Usage in Phase 10 |
|---|---|---|
| `ImportWizardService` | `src/services/import_wizard_service.py` | Extended to accept a `DataConnector` as an alternative data source; existing CSV/Excel path preserved |
| `ImportWizardView` | `src/ui/views/import_wizard_view.py` | Step 1 gains a source-type toggle; Steps 1b and 2 extended with DB-specific panels |
| `SettingsView` | `src/ui/views/settings_view.py` | New "Connections" tab added alongside existing General and Scheduled Reports tabs |
| `SettingsService` | `src/services/settings_service.py` | `get("connector_key")` retrieves the auto-generated Fernet key; `set("connector_key", key)` persists it |
| `AuditService` | `src/services/audit_service.py` | Stock transfer state changes and connection CRUD emit `AuditEvent` records |
| `AuthService` | `src/services/auth_service.py` | `require_role()` enforces RBAC on `ConnectionService` (ADMIN-only create/delete) and `StockTransferService.cancel()` (MANAGER+) |
| `TranslationService` + `I18nMixin` | `src/services/translation_service.py`, `src/ui/mixins/i18n_mixin.py` | `LocationsView` and `StockTransferView` implement `I18nMixin`; all new strings wrapped in `_()` |
| `DataTable` | `src/ui/widgets/data_table.py` | Location stock summary table, transfer pipeline table, connection profile list |
| `KPICard` | `src/ui/widgets/kpi_card.py` | Location-aware stock KPIs in `DashboardView` |
| `DatabaseManager` | `src/database/connection.py` | Session factory for all Phase 10 repositories |
| `LoggerMixin` | `src/logger.py` | Logging in all new Phase 10 modules |
| `tools/extract_strings.py` | `tools/extract_strings.py` | Run after Phase 10 string additions to verify catalog completeness |

---

## 3. Architecture Overview

### 3.1 Phase 10 Directory Structure

```
logistics-dss/
├── src/
│   ├── connectors/                             # NEW package
│   │   ├── __init__.py
│   │   ├── base.py                             # NEW: DataConnector ABC + ConnectorError
│   │   ├── csv_connector.py                    # NEW: CSVConnector (formalised from ImportWizardService)
│   │   ├── postgresql_connector.py             # NEW: PostgreSQLConnector (psycopg2-binary)
│   │   ├── mysql_connector.py                  # NEW: MySQLConnector (PyMySQL)
│   │   ├── sqlite_connector.py                 # NEW: SQLiteConnector (external SQLite file)
│   │   └── odbc_connector.py                   # NEW: GenericODBCConnector (pyodbc)
│   ├── database/
│   │   └── models.py                           # + ConnectionProfile, Location, ProductLocation, StockTransfer
│   ├── repositories/
│   │   ├── connection_profile_repository.py    # NEW
│   │   ├── location_repository.py              # NEW
│   │   ├── product_location_repository.py      # NEW
│   │   └── stock_transfer_repository.py        # NEW
│   ├── services/
│   │   ├── connection_service.py               # NEW: CRUD + test_connection + factory + Fernet encryption
│   │   ├── location_service.py                 # NEW: CRUD + get_stock_by_location + atomic move_stock
│   │   └── stock_transfer_service.py           # NEW: create_draft + dispatch + receive + cancel
│   └── ui/
│       ├── app.py                              # (existing) + LocationsView + StockTransferView nav
│       └── views/
│           ├── locations_view.py               # NEW: location CRUD + per-location stock summary
│           ├── stock_transfer_view.py          # NEW: transfer pipeline
│           ├── settings_view.py                # (existing) + Connections tab
│           ├── import_wizard_view.py           # (existing) + Database source path
│           ├── inventory_view.py               # (existing) + location filter dropdown
│           ├── dashboard_view.py               # (existing) + location filter on KPI cards
│           ├── alerts_view.py                  # (existing) + location filter
│           └── executive_view.py               # (existing) + location filter
├── locale/
│   ├── en/LC_MESSAGES/logistics_dss.po         # + ~80 new strings
│   ├── pt_BR/LC_MESSAGES/logistics_dss.po      # + ~80 PT-BR translations
│   └── es/LC_MESSAGES/logistics_dss.po         # + ~80 ES translations
├── tests/
│   ├── test_connector_framework.py             # NEW: 10 tests
│   ├── test_connection_service.py              # NEW: 8 tests
│   ├── test_location_service.py                # NEW: 10 tests
│   ├── test_stock_transfer_service.py          # NEW: 10 tests
│   └── test_multi_location_inventory.py        # NEW: 7 tests
└── requirements.txt                            # + 4 new dependencies
```

### 3.2 Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     Presentation Layer (16 views + App)                       │
│                                                                                │
│  LocationsView          StockTransferView     SettingsView (+ Connections tab) │
│  InventoryView (+ loc)  DashboardView (+ loc) AlertsView (+ loc)               │
│  ImportWizardView (+ DB source path)          ExecutiveView (+ loc filter)     │
│                                                                                │
│  All new views implement I18nMixin; new strings in 3 locale catalogs           │
├──────────────────────────────────────────────────────────────────────────────┤
│                         Service Layer (Phase 10 additions)                     │
│  ┌─────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │  ConnectionService  │  │  LocationService      │  │ StockTransferService │ │
│  │  CRUD + test +      │  │  CRUD + stock query + │  │ draft + dispatch +   │ │
│  │  factory + Fernet   │  │  atomic move_stock()  │  │ receive + cancel     │ │
│  └─────────────────────┘  └──────────────────────┘  └──────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                         Connector Layer (Phase 10 NEW)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐ │
│  │ CSVConnector │  │ PostgreSQL   │  │  MySQL   │  │ SQLite │  │   ODBC   │ │
│  │              │  │ Connector    │  │ Connector│  │Connector│  │Connector │ │
│  └──────────────┘  └──────────────┘  └──────────┘  └────────┘  └──────────┘ │
│                         DataConnector ABC (base.py)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                      Repository Layer (Phase 10 additions)                     │
│  ConnectionProfileRepository  LocationRepository  ProductLocationRepository    │
│  StockTransferRepository                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                         ORM / Database Layer (SQLite)                          │
│  ConnectionProfile   Location   ProductLocation   StockTransfer                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 `DataConnector` ABC (`src/connectors/base.py`)

The `DataConnector` abstract base class defines a uniform interface for all data source connectors. Every connector implements three methods: `test_connection()` (health check, never raises — returns bool), `list_tables()` (returns available table/view/sheet names), and `fetch_dataframe()` (returns a pandas `DataFrame`). A `ConnectorError` exception class wraps driver-specific exceptions for uniform error handling in the service layer.

```python
"""
src/connectors/base.py — DataConnector abstract base class and ConnectorError.

All connectors implement:
    test_connection()  → bool           (never raises; False on failure)
    list_tables()      → list[str]      (table/view/sheet names)
    fetch_dataframe()  → pd.DataFrame   (raises ConnectorError on failure)
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class ConnectorError(Exception):
    """Raised by DataConnector implementations on connection or query failure."""


class DataConnector(ABC):
    """Abstract base for all ERP/database data source connectors."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the data source is reachable; False otherwise. Must not raise."""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Return a sorted list of table, view, or sheet names in the data source."""

    @abstractmethod
    def fetch_dataframe(self, source: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch data from `source` as a pandas DataFrame.

        Args:
            source: Table name, SQL query, or file path, depending on connector type.
            limit:  If provided, return at most `limit` rows (preview mode for Step 2).

        Raises:
            ConnectorError: On connection failure, missing table, or query error.
        """

    @property
    @abstractmethod
    def driver_type(self) -> str:
        """Return the driver type constant (e.g. CONNECTOR_POSTGRESQL)."""
```

| Method | Returns | Raises | Description |
|---|---|---|---|
| `test_connection()` | `bool` | Never | Validates connectivity; returns `False` on any error; safe to call on a background thread |
| `list_tables()` | `list[str]` | `ConnectorError` | Introspects the data source for importable entities |
| `fetch_dataframe(source, limit)` | `pd.DataFrame` | `ConnectorError` | Retrieves data; `limit` enables the Step 2 preview (first 10 rows shown in `ImportWizardView`) |
| `driver_type` (property) | `str` | — | Returns the constant stored in `ConnectionProfile.driver` |

---

### 4.2 Concrete Connector Implementations

**`CSVConnector` (`src/connectors/csv_connector.py`):**
Formalises the CSV/Excel parsing path currently embedded in `ImportWizardService`. Accepts a `file_path` string at construction. `list_tables()` returns `[Path(file_path).name]` (single sheet name). `fetch_dataframe()` dispatches to `pd.read_csv()` or `pd.read_excel()` based on file extension, preserving the Phase 8 fix for leading-zero SKU columns (`dtype={col: str}`).

**`PostgreSQLConnector` (`src/connectors/postgresql_connector.py`):**
Wraps `psycopg2.connect()`. `list_tables()` queries `information_schema.tables` filtered to `table_schema = 'public'` and `table_type IN ('BASE TABLE', 'VIEW')`. `fetch_dataframe()` uses `pd.read_sql_query()` with the psycopg2 connection; applies `LIMIT {limit}` when `limit` is set.

```python
class PostgreSQLConnector(DataConnector):

    def __init__(self, host: str, port: int, database: str,
                 username: str, password: str) -> None:
        self._dsn = f"host={host} port={port} dbname={database} " \
                    f"user={username} password={password} connect_timeout=5"

    def test_connection(self) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(self._dsn)
            conn.close()
            return True
        except Exception:
            return False

    def list_tables(self) -> list[str]:
        import psycopg2
        try:
            conn = psycopg2.connect(self._dsn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "  AND table_type IN ('BASE TABLE', 'VIEW') "
                    "ORDER BY table_name;"
                )
                return [row[0] for row in cur.fetchall()]
        except Exception as exc:
            raise ConnectorError(str(exc)) from exc
        finally:
            conn.close()

    def fetch_dataframe(self, source: str, limit: Optional[int] = None) -> pd.DataFrame:
        import psycopg2
        query = f"SELECT * FROM {source}"
        if limit:
            query += f" LIMIT {limit}"
        try:
            conn = psycopg2.connect(self._dsn)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as exc:
            raise ConnectorError(str(exc)) from exc

    @property
    def driver_type(self) -> str:
        return CONNECTOR_POSTGRESQL
```

**`MySQLConnector` (`src/connectors/mysql_connector.py`):**
Identical pattern using `PyMySQL.connect()`. `list_tables()` queries `information_schema.tables` filtered by `TABLE_SCHEMA = database`. `fetch_dataframe()` uses `pd.read_sql_query()`.

**`SQLiteConnector` (`src/connectors/sqlite_connector.py`):**
Wraps `sqlite3.connect(file_path)` for an external SQLite database file (not the application's own `logistics.db`). `list_tables()` queries `sqlite_master WHERE type IN ('table', 'view')`.

**`GenericODBCConnector` (`src/connectors/odbc_connector.py`):**
Wraps `pyodbc.connect(connection_string)`. Accepts a raw ODBC connection string (e.g. `Driver={ODBC Driver 17 for SQL Server};Server=...`). `list_tables()` uses `pyodbc.Cursor.tables()`. Marked optional in `requirements.txt` (comment); installation documented in README.

---

### 4.3 `ConnectionProfile` ORM Model

```python
class ConnectionProfile(Base):
    __tablename__ = "connection_profiles"

    id                 = Column(Integer, primary_key=True)
    name               = Column(String(100), nullable=False, unique=True)
    driver             = Column(String(20), nullable=False)
    # CSV | POSTGRESQL | MYSQL | SQLITE | ODBC
    host               = Column(String(255))
    port               = Column(Integer)
    database           = Column(String(255))
    username           = Column(String(100))
    encrypted_password = Column(Text)        # Fernet-encrypted; None for CSV/SQLite (no auth)
    connection_string  = Column(Text)        # ODBC only; overrides host/port/database
    active             = Column(Boolean, default=True, nullable=False)
    created_at         = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_tested_at     = Column(DateTime)
    last_test_ok       = Column(Boolean)

    __table_args__ = (
        Index("ix_connection_profile_name", "name"),
        Index("ix_connection_profile_driver", "driver"),
    )
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `name` | `String(100)` | No | Human-readable label shown in dropdowns and the Connections tab list |
| `driver` | `String(20)` | No | `CONNECTOR_CSV` / `CONNECTOR_POSTGRESQL` / `CONNECTOR_MYSQL` / `CONNECTOR_SQLITE` / `CONNECTOR_ODBC` |
| `host`, `port`, `database`, `username` | Various | Yes | Standard DB connection fields; unused for ODBC (uses `connection_string`) |
| `encrypted_password` | `Text` | Yes | Fernet-encrypted UTF-8 bytes stored as base64 string; `None` for CSV/SQLite connectors |
| `connection_string` | `Text` | Yes | Raw ODBC connection string; used only when `driver = CONNECTOR_ODBC` |
| `active` | `Boolean` | No | Inactive profiles are excluded from the Import Wizard source dropdown |
| `last_tested_at`, `last_test_ok` | `DateTime`, `Boolean` | Yes | Updated by `ConnectionService.test_connection()`; displayed in the Connections tab |

---

### 4.4 `ConnectionService` (`src/services/connection_service.py`)

```python
"""
ConnectionService — CRUD for ConnectionProfile + connector factory + Fernet encryption.

Password encryption key is stored in config/settings.json as "connector_key".
It is auto-generated (Fernet.generate_key()) on first use and persisted via SettingsService.
"""

from cryptography.fernet import Fernet
from src.services.settings_service import SettingsService
from src.connectors.base import DataConnector
from src.repositories.connection_profile_repository import ConnectionProfileRepository


class ConnectionService:

    def __init__(self, repo: ConnectionProfileRepository,
                 settings: SettingsService) -> None:
        self._repo = repo
        self._settings = settings

    # ── Fernet key management ──────────────────────────────────────────────────

    def _get_fernet(self) -> Fernet:
        key = self._settings.get("connector_key")
        if not key:
            key = Fernet.generate_key().decode()
            self._settings.set("connector_key", key)
        return Fernet(key.encode())

    def encrypt_password(self, plaintext: str) -> str:
        return self._get_fernet().encrypt(plaintext.encode()).decode()

    def decrypt_password(self, encrypted: str) -> str:
        return self._get_fernet().decrypt(encrypted.encode()).decode()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_profile(self, name: str, driver: str, *,
                       host: str = None, port: int = None,
                       database: str = None, username: str = None,
                       password: str = None,
                       connection_string: str = None,
                       actor: str) -> ConnectionProfile:
        AuthService.require_role(actor, role=ROLE_ADMIN)
        encrypted = self.encrypt_password(password) if password else None
        profile = self._repo.create(
            name=name, driver=driver, host=host, port=port,
            database=database, username=username,
            encrypted_password=encrypted,
            connection_string=connection_string,
        )
        AuditService.log(event_type="CONNECTION_PROFILE_CREATED",
                         actor=actor, entity_type="ConnectionProfile",
                         entity_id=profile.id)
        return profile

    def update_profile(self, profile_id: int, actor: str, **fields) -> ConnectionProfile:
        AuthService.require_role(actor, role=ROLE_ADMIN)
        if "password" in fields:
            fields["encrypted_password"] = self.encrypt_password(fields.pop("password"))
        return self._repo.update(profile_id, **fields)

    def delete_profile(self, profile_id: int, actor: str) -> None:
        AuthService.require_role(actor, role=ROLE_ADMIN)
        self._repo.delete(profile_id)
        AuditService.log(event_type="CONNECTION_PROFILE_DELETED",
                         actor=actor, entity_type="ConnectionProfile",
                         entity_id=profile_id)

    def list_active_profiles(self) -> list[ConnectionProfile]:
        return self._repo.list_active()

    # ── Connection testing ────────────────────────────────────────────────────

    def test_connection(self, profile_id: int) -> bool:
        """Instantiate the connector and call test_connection(); persist result."""
        profile = self._repo.get(profile_id)
        connector = self.get_connector(profile)
        ok = connector.test_connection()
        self._repo.update(profile_id,
                          last_tested_at=datetime.utcnow(),
                          last_test_ok=ok)
        return ok

    # ── Connector factory ─────────────────────────────────────────────────────

    def get_connector(self, profile: ConnectionProfile) -> DataConnector:
        """Return the appropriate DataConnector subclass for the given profile."""
        password = (self.decrypt_password(profile.encrypted_password)
                    if profile.encrypted_password else "")
        if profile.driver == CONNECTOR_POSTGRESQL:
            from src.connectors.postgresql_connector import PostgreSQLConnector
            return PostgreSQLConnector(profile.host, profile.port,
                                       profile.database, profile.username, password)
        if profile.driver == CONNECTOR_MYSQL:
            from src.connectors.mysql_connector import MySQLConnector
            return MySQLConnector(profile.host, profile.port,
                                  profile.database, profile.username, password)
        if profile.driver == CONNECTOR_SQLITE:
            from src.connectors.sqlite_connector import SQLiteConnector
            return SQLiteConnector(profile.database)
        if profile.driver == CONNECTOR_ODBC:
            from src.connectors.odbc_connector import GenericODBCConnector
            return GenericODBCConnector(profile.connection_string)
        if profile.driver == CONNECTOR_CSV:
            from src.connectors.csv_connector import CSVConnector
            return CSVConnector(profile.database)  # database field stores file path for CSV
        raise ValueError(f"Unknown driver type: {profile.driver!r}")
```

---

### 4.5 SettingsView Connections Tab

The `SettingsView` gains a `CTkTabview` with three tabs: **General** (existing settings), **Scheduled Reports** (existing scheduler panel), and **Connections** (new Phase 10 tab).

The Connections tab layout:

```
┌─ CONNECTIONS ──────────────────────────────────────────────────────────────┐
│  [+ Add Connection]                                          [Test] [Delete] │
│ ┌────────────────────────────────────────────────────────────────────────┐  │
│ │ Name              Driver       Host           Last Tested   Status     │  │
│ │ ─────────────────────────────────────────────────────────────────────  │  │
│ │ Production PG     PostgreSQL   db.erp.local   2026-02-25    ✓ OK       │  │
│ │ Legacy MySQL      MySQL        192.168.1.42   2026-02-24    ✓ OK       │  │
│ │ Supplier ODBC     ODBC         (string)       Never         — Untested │  │
│ └────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

The **Add / Edit Connection** modal (`CTkToplevel`) contains:
- Name field (`CTkEntry`)
- Driver type selector (`CTkOptionMenu`: CSV File, PostgreSQL, MySQL, SQLite File, Generic ODBC)
- Dynamic field section: Host, Port, Database/File Path, Username, Password (driver-appropriate fields shown/hidden based on selection)
- ODBC-only field: Connection String (`CTkTextbox`, full-width)
- **Test Connection** button: calls `ConnectionService.test_connection()` on a background thread; shows spinner; displays ✓ OK / ✗ Failed badge on completion
- Save / Cancel buttons

Only ADMIN users see the Add / Delete / Test buttons; OPERATOR and VIEWER see the list read-only.

---

### 4.6 ImportWizardView — Database Source Path

Phase 10 extends the Import Wizard with an alternative data source. Step 1 gains a **Source Type** radio-button pair:

```
  ● Browse File       ○ Database Connection
```

When "Browse File" is selected, the existing file picker and format dropdown are shown (Phase 8 behaviour). When "Database Connection" is selected, the file picker is hidden and a connection dropdown appears:

```
  Connection:  [Production PG  ▼]        [Refresh list]
```

Step 2 (currently "File Preview") becomes context-aware:
- **File source**: existing preview behaviour (first 10 rows of the selected file)
- **Database source**: a **Table Picker** panel — calls `DataConnector.list_tables()` in a background thread; shows the result in a `DataTable`; user selects one row; Next is enabled when a table is selected

Step 3 onwards (column mapping, validation, import commit) are unchanged — `ImportWizardService.preview()` and `ImportWizardService.commit()` now accept an optional `connector: DataConnector` argument. When provided, `preview()` calls `connector.fetch_dataframe(selected_table, limit=10)` instead of parsing a file; `commit()` calls `connector.fetch_dataframe(selected_table)` for the full dataset.

---

### 4.7 `Location` ORM Model

```python
class Location(Base):
    __tablename__ = "locations"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(100), nullable=False, unique=True)
    code       = Column(String(20), nullable=False, unique=True)
    type       = Column(String(20), nullable=False)  # WAREHOUSE | STORE | DC
    address    = Column(Text)
    active     = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_location_code", "code", unique=True),
        Index("ix_location_type", "type"),
    )

    product_locations    = relationship("ProductLocation", back_populates="location",
                                        cascade="all, delete-orphan")
    outbound_transfers   = relationship("StockTransfer",
                                        foreign_keys="StockTransfer.from_location_id",
                                        back_populates="from_location")
    inbound_transfers    = relationship("StockTransfer",
                                        foreign_keys="StockTransfer.to_location_id",
                                        back_populates="to_location")
```

| Column | Type | Description |
|---|---|---|
| `code` | `String(20)` | Short identifier used in transfer references (e.g. `"WH-01"`, `"DC-NORTH"`) |
| `type` | `String(20)` | `LOCATION_WAREHOUSE` / `LOCATION_STORE` / `LOCATION_DC` (distribution centre) |
| `address` | `Text` | Optional free-text physical address for documentation |

---

### 4.8 `ProductLocation` ORM Model

```python
class ProductLocation(Base):
    __tablename__ = "product_locations"

    id              = Column(Integer, primary_key=True)
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id     = Column(Integer, ForeignKey("locations.id"), nullable=False)
    current_stock   = Column(Float, default=0.0, nullable=False)
    reserved_stock  = Column(Float, default=0.0, nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "location_id",
                         name="uq_product_location"),
        Index("ix_product_location_product", "product_id"),
        Index("ix_product_location_location", "location_id"),
    )

    product  = relationship("Product", back_populates="locations")
    location = relationship("Location", back_populates="product_locations")
```

`reserved_stock` tracks quantities committed to outbound `DRAFT` transfers — stock that is logically unavailable for new transfers even though the goods have not yet physically departed. Available stock = `current_stock - reserved_stock`.

---

### 4.9 `StockTransfer` ORM Model

```python
class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id               = Column(Integer, primary_key=True)
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    to_location_id   = Column(Integer, ForeignKey("locations.id"), nullable=False)
    product_id       = Column(Integer, ForeignKey("products.id"), nullable=False)
    qty              = Column(Float, nullable=False)
    status           = Column(String(20), default="DRAFT", nullable=False)
    # DRAFT | IN_TRANSIT | RECEIVED | CANCELLED
    initiated_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    initiated_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    dispatched_at    = Column(DateTime)
    received_at      = Column(DateTime)
    notes            = Column(Text)

    __table_args__ = (
        Index("ix_stock_transfer_status", "status"),
        Index("ix_stock_transfer_product", "product_id"),
        Index("ix_stock_transfer_from_loc", "from_location_id"),
        Index("ix_stock_transfer_to_loc", "to_location_id"),
    )

    from_location = relationship("Location",
                                  foreign_keys=[from_location_id],
                                  back_populates="outbound_transfers")
    to_location   = relationship("Location",
                                  foreign_keys=[to_location_id],
                                  back_populates="inbound_transfers")
    product       = relationship("Product")
    initiator     = relationship("User", foreign_keys=[initiated_by])
```

**Transfer status transitions:**

```
DRAFT ──────────── dispatch() ──────────► IN_TRANSIT ─── receive() ──► RECEIVED
  │                                            │
  └── cancel() ──────────────────────── cancel() (MANAGER+) ──────────► CANCELLED
```

---

### 4.10 `LocationService` (`src/services/location_service.py`)

```python
class LocationService:

    def create_location(self, name: str, code: str, type_: str,
                        address: str = None, actor: str = None) -> Location:
        AuthService.require_role(actor, role=ROLE_MANAGER)
        if type_ not in LOCATION_TYPES:
            raise ValueError(f"Invalid location type: {type_!r}")
        location = self._repo.create(name=name, code=code.upper(),
                                     type=type_, address=address)
        AuditService.log("LOCATION_CREATED", actor=actor,
                         entity_type="Location", entity_id=location.id)
        return location

    def get_stock_by_location(self, location_id: int) -> list[dict]:
        """
        Return per-product stock levels at `location_id`.

        Returns:
            list of dicts: {product_id, sku, name, current_stock, reserved_stock,
                             available_stock, reorder_point}
        """
        rows = self._pl_repo.list_by_location(location_id)
        return [
            {
                "product_id":      pl.product_id,
                "sku":             pl.product.sku,
                "name":            pl.product.name,
                "current_stock":   pl.current_stock,
                "reserved_stock":  pl.reserved_stock,
                "available_stock": pl.current_stock - pl.reserved_stock,
                "reorder_point":   pl.product.reorder_point,
            }
            for pl in rows
        ]

    def get_all_locations_summary(self) -> list[dict]:
        """Return all active locations with aggregate stock counts."""
        locations = self._repo.list_active()
        return [
            {
                "id":         loc.id,
                "name":       loc.name,
                "code":       loc.code,
                "type":       loc.type,
                "sku_count":  self._pl_repo.count_by_location(loc.id),
                "total_stock": self._pl_repo.sum_current_stock(loc.id),
            }
            for loc in locations
        ]

    def move_stock(self, from_location_id: int, to_location_id: int,
                   product_id: int, qty: float, actor: str) -> None:
        """
        Atomically decrement from_location and increment to_location stock.
        Used by StockTransferService.receive(); both updates within a single session.
        """
        with self._session_factory() as session:
            from_pl = session.query(ProductLocation).filter_by(
                product_id=product_id, location_id=from_location_id).with_for_update().one()
            to_pl = session.query(ProductLocation).filter_by(
                product_id=product_id, location_id=to_location_id).with_for_update().first()
            if from_pl.current_stock < qty:
                raise InsufficientStockError(
                    f"Available: {from_pl.current_stock:.2f}, requested: {qty:.2f}")
            from_pl.current_stock -= qty
            if to_pl is None:
                session.add(ProductLocation(
                    product_id=product_id, location_id=to_location_id,
                    current_stock=qty, reserved_stock=0.0))
            else:
                to_pl.current_stock += qty
            session.commit()
```

| Method | RBAC | Description |
|---|---|---|
| `create_location()` | MANAGER+ | Validates type; upcases code; emits audit event |
| `update_location()` | MANAGER+ | Partial field updates; audit event |
| `deactivate_location()` | ADMIN | Checks no DRAFT or IN_TRANSIT transfers before deactivating |
| `get_stock_by_location()` | OPERATOR+ | Per-product stock for a single location |
| `get_all_locations_summary()` | OPERATOR+ | Aggregate view across all active locations |
| `move_stock()` | Internal | Called by `StockTransferService.receive()`; uses `SELECT ... FOR UPDATE` for concurrency safety |

---

### 4.11 `StockTransferService` (`src/services/stock_transfer_service.py`)

```python
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT":      {"IN_TRANSIT", "CANCELLED"},
    "IN_TRANSIT": {"RECEIVED",   "CANCELLED"},
    "RECEIVED":   set(),
    "CANCELLED":  set(),
}


class StockTransferService:

    def create_draft(self, from_location_id: int, to_location_id: int,
                     product_id: int, qty: float,
                     notes: str = None, actor_id: int = None) -> StockTransfer:
        if qty <= 0:
            raise ValueError("Transfer quantity must be positive.")
        if from_location_id == to_location_id:
            raise ValueError("Source and destination locations must differ.")
        pl = self._pl_repo.get(product_id, from_location_id)
        available = (pl.current_stock - pl.reserved_stock) if pl else 0.0
        if available < qty:
            raise InsufficientStockError(
                f"Available at source: {available:.2f}, requested: {qty:.2f}")
        # Reserve stock at source location
        self._pl_repo.increment_reserved(product_id, from_location_id, qty)
        transfer = self._repo.create(
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            product_id=product_id, qty=qty,
            status="DRAFT", initiated_by=actor_id,
            notes=notes,
        )
        AuditService.log("STOCK_TRANSFER_CREATED", actor=str(actor_id),
                         entity_type="StockTransfer", entity_id=transfer.id,
                         detail={"qty": qty, "from": from_location_id,
                                 "to": to_location_id})
        return transfer

    def dispatch(self, transfer_id: int, actor: str) -> StockTransfer:
        transfer = self._get_and_validate_transition(transfer_id, "IN_TRANSIT")
        # Decrement source: current_stock -= qty, reserved_stock -= qty
        self._pl_repo.decrement_current_and_reserved(
            transfer.product_id, transfer.from_location_id, transfer.qty)
        self._repo.update(transfer_id,
                          status="IN_TRANSIT", dispatched_at=datetime.utcnow())
        AuditService.log("STOCK_TRANSFER_DISPATCHED", actor=actor,
                         entity_type="StockTransfer", entity_id=transfer_id)
        return self._repo.get(transfer_id)

    def receive(self, transfer_id: int, actor: str) -> StockTransfer:
        transfer = self._get_and_validate_transition(transfer_id, "RECEIVED")
        # Increment destination: current_stock += qty
        self._location_service.move_stock(
            from_location_id=transfer.from_location_id,
            to_location_id=transfer.to_location_id,
            product_id=transfer.product_id,
            qty=0.0,   # source already decremented on dispatch; only increment destination
            actor=actor,
        )
        self._pl_repo.increment_current(
            transfer.product_id, transfer.to_location_id, transfer.qty)
        self._repo.update(transfer_id,
                          status="RECEIVED", received_at=datetime.utcnow())
        AuditService.log("STOCK_TRANSFER_RECEIVED", actor=actor,
                         entity_type="StockTransfer", entity_id=transfer_id)
        return self._repo.get(transfer_id)

    def cancel(self, transfer_id: int, actor: str) -> StockTransfer:
        transfer = self._get_and_validate_transition(transfer_id, "CANCELLED")
        if transfer.status == "IN_TRANSIT":
            AuthService.require_role(actor, role=ROLE_MANAGER)
            # Rollback: restore source current_stock
            self._pl_repo.increment_current(
                transfer.product_id, transfer.from_location_id, transfer.qty)
        elif transfer.status == "DRAFT":
            # Release reservation
            self._pl_repo.decrement_reserved(
                transfer.product_id, transfer.from_location_id, transfer.qty)
        self._repo.update(transfer_id, status="CANCELLED")
        AuditService.log("STOCK_TRANSFER_CANCELLED", actor=actor,
                         entity_type="StockTransfer", entity_id=transfer_id)
        return self._repo.get(transfer_id)
```

**Stock balance invariants enforced by `StockTransferService`:**

| Event | Effect on `ProductLocation` |
|---|---|
| `create_draft()` | `from_location.reserved_stock += qty` |
| `dispatch()` | `from_location.current_stock -= qty`; `from_location.reserved_stock -= qty` |
| `receive()` | `to_location.current_stock += qty` |
| `cancel()` (DRAFT) | `from_location.reserved_stock -= qty` |
| `cancel()` (IN_TRANSIT) | `from_location.current_stock += qty` |

---

### 4.12 `LocationsView` (`src/ui/views/locations_view.py`)

The `LocationsView` presents a two-panel layout:

**Top panel — Location List:**
```
[+ Add Location]  [Edit]  [Deactivate]                     [ All Types ▼]
┌──────────────────────────────────────────────────────────────────────────┐
│  Code     Name                    Type        SKUs   Total Stock  Active │
│  ──────────────────────────────────────────────────────────────────────  │
│  WH-01    Main Warehouse          WAREHOUSE   184    92,450 units   ✓   │
│  DC-NORTH Northern DC             DC           72    34,820 units   ✓   │
│  STR-01   Retail Store — Central  STORE        38     4,210 units   ✓   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Bottom panel — Per-Location Stock (updates on row selection above):**
```
  Stock at: Main Warehouse (WH-01)
┌──────────────────────────────────────────────────────────────────────────┐
│  SKU       Name              Current Stock  Reserved  Available  Reorder │
│  ────────────────────────────────────────────────────────────────────── │
│  SKU-0042  Widget A          1,200          200        1,000       500   │
│  SKU-0078  Widget B            480            0          480       200   │
└──────────────────────────────────────────────────────────────────────────┘
```

Add/Edit Location modal fields: Name, Code (auto-upcased), Type (WAREHOUSE / STORE / DC dropdown), Address (optional multiline). MANAGER role required to save; OPERATOR sees the list read-only.

---

### 4.13 `StockTransferView` (`src/ui/views/stock_transfer_view.py`)

A pipeline view modelled after the existing `PurchaseOrdersView`:

```
[+ New Transfer]  [Dispatch]  [Receive]  [Cancel]      [ All Status ▼] [ All Products ▼]
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  ID     Product        From        To          Qty    Status      Initiated   Notes  │
│  ────────────────────────────────────────────────────────────────────────────────── │
│  T-004  Widget A       WH-01       DC-NORTH    200    IN_TRANSIT  2026-02-25         │
│  T-005  Widget B       DC-NORTH    STR-01       80    DRAFT       2026-02-25  urgent │
│  T-003  Widget C       WH-01       STR-01      500    RECEIVED    2026-02-24         │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Buttons are conditionally enabled based on the selected row's status:
- **Dispatch**: enabled for DRAFT transfers (OPERATOR+)
- **Receive**: enabled for IN_TRANSIT transfers (OPERATOR+)
- **Cancel**: enabled for DRAFT (OPERATOR+) or IN_TRANSIT (MANAGER+)

The **New Transfer** modal presents: Source Location dropdown, Destination Location dropdown, Product dropdown (with available stock at source shown as a hint), Quantity entry (validated against available stock), Notes field.

---

### 4.14 Location Filter in Existing Views

Four existing views gain a Location filter `CTkOptionMenu` in their toolbar:

```
  Location: [All Locations ▼]
```

| View | Filter behaviour |
|---|---|
| `InventoryView` | Queries `ProductLocation` joined to `Product`; shows per-location stock instead of aggregate stock when a location is selected |
| `DashboardView` | KPI cards (Total SKUs, Low-Stock Items, Total Inventory Value) recompute for the selected location; "All Locations" shows the cross-location aggregate |
| `AlertsView` | Low-stock and reorder alerts filtered to the selected location's `ProductLocation.current_stock` vs `Product.reorder_point` |
| `ExecutiveView` | Stock Value and Low-Stock KPIs recomputed per location |

The filter defaults to "All Locations" on view load. The selected location is persisted only for the session (not saved to `settings.json`).

---

## 5. Data Flow

### 5.1 Database Connection Setup Flow

```
ADMIN user opens SettingsView → Connections tab
    │
    ▼
Click [+ Add Connection]
    ├── Modal opens: selects "PostgreSQL" driver
    ├── Host = "db.erp.corp", Port = 5432, DB = "erp_prod", User = "reports", Password = "..."
    └── Click [Test Connection]
            │
            ▼
        ConnectionService.test_connection(profile_id=None)    ← inline test before save
            ├── Builds PostgreSQLConnector from modal fields (not yet persisted)
            └── connector.test_connection() → True
                    ├── Modal shows ✓ Connected
                    └── [Save] button enabled
                            │
                            ▼
                ConnectionService.create_profile(name="ERP PostgreSQL", driver="POSTGRESQL", ...)
                    ├── encrypt_password("...") → Fernet ciphertext
                    ├── ConnectionProfileRepository.create(...)
                    ├── AuditService.log("CONNECTION_PROFILE_CREATED", ...)
                    └── Returns saved ConnectionProfile(id=1, ...)

Connections tab refreshes; new row visible:
    "ERP PostgreSQL    PostgreSQL    db.erp.corp    Just now    ✓ OK"
```

### 5.2 Database Import Flow

```
User opens Import Wizard
    │
Step 1: Source Type = "Database Connection"
    ├── Connection dropdown: selects "ERP PostgreSQL"
    └── Click Next
            │
            ▼
Step 1b: Table Picker
    ├── Background thread: ConnectionService.get_connector(profile=1)
    │       → PostgreSQLConnector(host="db.erp.corp", ...)
    ├── connector.list_tables()
    │       → ["demand_history", "product_master", "supplier_master", ...]
    └── DataTable shows table list; user selects "product_master"
            │
            ▼
Step 2: Preview
    ├── connector.fetch_dataframe("product_master", limit=10)
    │       → DataFrame(10 rows × 8 columns)
    └── Preview table rendered; column mapping dropdowns populated

Step 3: Column Mapping → Step 4: Validation → Step 5: Commit
    └── ImportWizardService.commit(connector=connector, selected_table="product_master",
                                   import_type="PRODUCT", ...)
            ├── connector.fetch_dataframe("product_master") → full DataFrame
            ├── Existing per-row validation, overwrite/skip logic (Phase 8)
            └── AuditEvent("IMPORT_COMMITTED", detail={"source": "ERP PostgreSQL",
                           "table": "product_master", "rows_imported": 142, ...})
```

### 5.3 Stock Transfer Lifecycle

```
OPERATOR creates new transfer in StockTransferView:
    ├── From: WH-01, To: DC-NORTH, Product: Widget A (SKU-0042), Qty: 200
    │
    ▼
StockTransferService.create_draft(from_location_id=1, to_location_id=2,
                                   product_id=42, qty=200, actor_id=5)
    ├── Validates: qty > 0 ✓; from ≠ to ✓
    ├── ProductLocation(product=42, location=1): current_stock=1200, reserved=0
    │       available = 1200 - 0 = 1200 ≥ 200 ✓
    ├── ProductLocationRepository.increment_reserved(42, 1, 200)
    │       → ProductLocation.reserved_stock = 200
    ├── StockTransferRepository.create(status="DRAFT", ...)
    │       → StockTransfer(id=7, status="DRAFT")
    └── AuditEvent("STOCK_TRANSFER_CREATED", entity_id=7)

OPERATOR selects T-007 in pipeline → clicks [Dispatch]:
    └── StockTransferService.dispatch(transfer_id=7, actor="jsmith")
            ├── ProductLocationRepository.decrement_current_and_reserved(42, 1, 200)
            │       → current_stock=1000, reserved_stock=0
            └── StockTransfer.status = "IN_TRANSIT"; dispatched_at = now()

OPERATOR at DC-NORTH receives shipment → selects T-007 → clicks [Receive]:
    └── StockTransferService.receive(transfer_id=7, actor="alopez")
            ├── ProductLocationRepository.increment_current(42, 2, 200)
            │       → ProductLocation(product=42, location=2).current_stock += 200
            └── StockTransfer.status = "RECEIVED"; received_at = now()
                    AuditEvent("STOCK_TRANSFER_RECEIVED", ...)
```

---

## 6. New Configuration Constants (`config/constants.py`)

| Constant | Value | Description |
|---|---|---|
| `CONNECTOR_CSV` | `"CSV"` | CSV / Excel flat-file connector |
| `CONNECTOR_POSTGRESQL` | `"POSTGRESQL"` | psycopg2-binary connector |
| `CONNECTOR_MYSQL` | `"MYSQL"` | PyMySQL connector |
| `CONNECTOR_SQLITE` | `"SQLITE"` | External SQLite file connector |
| `CONNECTOR_ODBC` | `"ODBC"` | Generic ODBC connector |
| `CONNECTOR_DRIVERS` | `(CSV, POSTGRESQL, MYSQL, SQLITE, ODBC)` | Ordered tuple for display in driver selector |
| `CONNECTOR_DISPLAY_NAMES` | `{"CSV": "CSV / Excel File", "POSTGRESQL": "PostgreSQL", ...}` | Display labels for `CTkOptionMenu` |
| `CONNECTOR_DEFAULT_PORTS` | `{"POSTGRESQL": 5432, "MYSQL": 3306, "SQLITE": None, "ODBC": None}` | Auto-populated Port field per driver selection |
| `CONNECTOR_TEST_TIMEOUT_S` | `5` | Seconds before `test_connection()` background thread is considered timed-out |
| `LOCATION_WAREHOUSE` | `"WAREHOUSE"` | Location type constant |
| `LOCATION_STORE` | `"STORE"` | Location type constant |
| `LOCATION_DC` | `"DC"` | Location type constant — distribution centre |
| `LOCATION_TYPES` | `("WAREHOUSE", "STORE", "DC")` | Valid location types |
| `TRANSFER_DRAFT` | `"DRAFT"` | StockTransfer status |
| `TRANSFER_IN_TRANSIT` | `"IN_TRANSIT"` | StockTransfer status |
| `TRANSFER_RECEIVED` | `"RECEIVED"` | StockTransfer status |
| `TRANSFER_CANCELLED` | `"CANCELLED"` | StockTransfer status |
| `TRANSFER_STATUSES` | `("DRAFT", "IN_TRANSIT", "RECEIVED", "CANCELLED")` | Valid statuses for filter dropdown |
| `IMPORT_SOURCE_FILE` | `"FILE"` | Import Wizard source type |
| `IMPORT_SOURCE_DATABASE` | `"DATABASE"` | Import Wizard source type |

---

## 7. Technology Stack (Phase 10 Additions)

| Capability | Package | Version | Usage |
|---|---|---|---|
| PostgreSQL connector | `psycopg2-binary` | `>=2.9.9` | Binary distribution avoids system `libpq` dependency; used in `PostgreSQLConnector` |
| MySQL/MariaDB connector | `PyMySQL` | `>=1.1.1` | Pure-Python; no system library required; used in `MySQLConnector` |
| ODBC connector | `pyodbc` | `>=5.1.0` | Requires system ODBC driver (ODBC Driver for SQL Server, unixODBC, etc.); listed in `requirements.txt` with a `# optional` comment |
| Symmetric encryption | `cryptography` | `>=42.0.5` | `Fernet` symmetric encryption for `ConnectionProfile.encrypted_password`; also used by the `paramiko` family if SSH tunnelling is added in future |

**`requirements.txt` additions:**

```
psycopg2-binary>=2.9.9
PyMySQL>=1.1.1
pyodbc>=5.1.0        # optional; requires system ODBC driver
cryptography>=42.0.5
```

**`packaging/logistics_dss.spec` — connector hiddenimports:**

```python
hiddenimports=[
    "passlib.handlers.bcrypt",     # Phase 8
    "psycopg2",                    # NEW Phase 10
    "PyMySQL",                     # NEW Phase 10
    "cryptography.fernet",         # NEW Phase 10
    "cryptography.hazmat.primitives.kdf.pbkdf2",  # transitive dep
],
```

`pyodbc` is excluded from the PyInstaller build by default (requires system driver). Its absence is handled gracefully: `GenericODBCConnector.__init__()` raises `ImportError` with a clear message if `pyodbc` is not installed.

---

## 8. Implementation Tasks

### 8.1 Connector Framework (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-01 | Add connector, location, and transfer constants to `config/constants.py` | `config/constants.py` | 20 min |
| T10-02 | Create `src/connectors/` package; implement `DataConnector` ABC + `ConnectorError` | `src/connectors/base.py` | 1 h |
| T10-03 | Implement `CSVConnector` (formalise ImportWizardService CSV/Excel path) | `src/connectors/csv_connector.py` | 1.5 h |
| T10-04 | Implement `PostgreSQLConnector` (psycopg2-binary; `list_tables` via `information_schema`) | `src/connectors/postgresql_connector.py` | 2 h |
| T10-05 | Implement `MySQLConnector` (PyMySQL; `list_tables` via `information_schema`) | `src/connectors/mysql_connector.py` | 1.5 h |
| T10-06 | Implement `SQLiteConnector` (external SQLite file; `sqlite_master` table listing) | `src/connectors/sqlite_connector.py` | 1 h |
| T10-07 | Implement `GenericODBCConnector` (pyodbc; `Cursor.tables()`; graceful `ImportError` if pyodbc absent) | `src/connectors/odbc_connector.py` | 1.5 h |

### 8.2 ConnectionProfile Model + Service (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-08 | Add `ConnectionProfile` ORM model + `ConnectionProfileRepository` (get, list_active, create, update, delete) | `src/database/models.py`, `src/repositories/connection_profile_repository.py` | 1.5 h |
| T10-09 | Implement `ConnectionService` (CRUD with RBAC, `encrypt_password`, `decrypt_password`, `test_connection`, `get_connector` factory; auto-generate Fernet key in `SettingsService`) | `src/services/connection_service.py` | 2.5 h |

### 8.3 SettingsView Connections Tab (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-10 | Add "Connections" tab to `SettingsView`; connection profile list with `DataTable`; Test and Delete buttons (ADMIN only) | `src/ui/views/settings_view.py` | 2 h |
| T10-11 | Add/Edit connection profile modal: driver selector, dynamic field panel, inline Test Connection button with background thread + spinner | `src/ui/views/settings_view.py` | 2.5 h |

### 8.4 ImportWizardView — Database Source Path (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-12 | Add Source Type radio selector to Step 1; show/hide file picker vs connection dropdown based on selection | `src/ui/views/import_wizard_view.py` | 1.5 h |
| T10-13 | Database path — Step 1b: connection picker; Step 2 table picker (background `list_tables()`, `DataTable` row selection, preview `fetch_dataframe(limit=10)`) | `src/ui/views/import_wizard_view.py` | 2.5 h |
| T10-14 | Update `ImportWizardService.preview()` and `commit()` to accept optional `connector: DataConnector` + `selected_table: str`; delegate to connector when provided | `src/services/import_wizard_service.py` | 1.5 h |

### 8.5 Multi-Location Models (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-15 | Add `Location` ORM model + `LocationRepository` (get, list_active, create, update, deactivate, list_by_type) | `src/database/models.py`, `src/repositories/location_repository.py` | 1.5 h |
| T10-16 | Add `ProductLocation` ORM model + `ProductLocationRepository` (get, list_by_location, list_by_product, increment/decrement helpers, sum_current_stock) | `src/database/models.py`, `src/repositories/product_location_repository.py` | 1.5 h |
| T10-17 | Add `StockTransfer` ORM model + `StockTransferRepository` (get, list_by_status, list_by_location, list_by_product, create, update) | `src/database/models.py`, `src/repositories/stock_transfer_repository.py` | 2 h |

### 8.6 Multi-Location Services (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-18 | Implement `LocationService` (CRUD with RBAC, `get_stock_by_location`, `get_all_locations_summary`, `move_stock` with `SELECT FOR UPDATE`) | `src/services/location_service.py` | 2.5 h |
| T10-19 | Implement `StockTransferService` (`create_draft` with reservation, `dispatch`, `receive`, `cancel` with rollback, `_VALID_TRANSITIONS` enforcement, full AuditEvent trail) | `src/services/stock_transfer_service.py` | 3 h |

### 8.7 Location UI (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-20 | `LocationsView`: two-panel layout (location list + per-location stock summary); Add/Edit/Deactivate modal; `I18nMixin` | `src/ui/views/locations_view.py` | 3 h |
| T10-21 | `StockTransferView`: transfer pipeline table; New Transfer modal; Dispatch/Receive/Cancel buttons with status-based enable logic; `I18nMixin` | `src/ui/views/stock_transfer_view.py` | 3 h |
| T10-22 | `InventoryView`: add Location filter `CTkOptionMenu`; wire to `LocationService.get_stock_by_location()` when specific location selected; "All Locations" uses existing aggregate path | `src/ui/views/inventory_view.py` | 2 h |
| T10-23 | `DashboardView`, `AlertsView`, `ExecutiveView`: add Location filter; pass `location_id` to `KPIService`, `AlertService`, `KPIService.get_executive_kpis()` respectively | `src/ui/views/dashboard_view.py` et al. | 1.5 h |
| T10-24 | Wire `LocationsView` and `StockTransferView` into `App` navigation sidebar; add to `_nav_buttons` i18n list | `src/ui/app.py` | 1 h |

### 8.8 i18n Extension (Priority: Medium)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-25 | Add ~80 new strings to all 3 locale `.po` files (EN + PT-BR + ES); recompile `.mo` files; run `tools/extract_strings.py --check-completeness` to verify 0 missing | `locale/*/LC_MESSAGES/logistics_dss.po` | 3 h |

### 8.9 Packaging (Priority: Medium)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-26 | Update `packaging/logistics_dss.spec` with Phase 10 `hiddenimports` (psycopg2, PyMySQL, cryptography.fernet); rebuild `.app`; smoke-test connector setup and stock transfer flow in bundle | `packaging/logistics_dss.spec` | 1.5 h |

### 8.10 Testing (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T10-27 | Write `tests/test_connector_framework.py` (10 tests: CSVConnector, SQLiteConnector, mock psycopg2 / PyMySQL, ConnectorError propagation, `test_connection()` return-False on failure) | `tests/test_connector_framework.py` | 2 h |
| T10-28 | Write `tests/test_connection_service.py` (8 tests: CRUD RBAC, Fernet round-trip, `get_connector()` factory dispatch, `test_connection()` persists result) | `tests/test_connection_service.py` | 1.5 h |
| T10-29 | Write `tests/test_location_service.py` (10 tests: CRUD, stock summary, `move_stock()` atomicity, `deactivate()` blocked by open transfers, `InsufficientStockError`) | `tests/test_location_service.py` | 2 h |
| T10-30 | Write `tests/test_stock_transfer_service.py` (10 tests: `create_draft` reserves stock, `dispatch` decrements, `receive` increments destination, `cancel` DRAFT releases reservation, `cancel` IN_TRANSIT rollback, invalid transition raises, MANAGER required for IN_TRANSIT cancel) | `tests/test_stock_transfer_service.py` | 2 h |
| T10-31 | Write `tests/test_multi_location_inventory.py` (7 tests: InventoryService location filter, AlertService location-aware threshold, `get_stock_by_location` available_stock = current − reserved, full end-to-end DRAFT→IN_TRANSIT→RECEIVED balance check) | `tests/test_multi_location_inventory.py` | 1.5 h |

**Total estimated effort: 50–65 hours (2.5–3 working days)**

---

## 9. Implementation Order

```
Step 1: Constants + Connector Infrastructure
  ├── T10-01: Phase 10 constants
  ├── T10-02: DataConnector ABC + ConnectorError
  ├── T10-03: CSVConnector
  ├── T10-04: PostgreSQLConnector
  ├── T10-05: MySQLConnector
  ├── T10-06: SQLiteConnector
  └── T10-07: GenericODBCConnector

Step 2: ConnectionProfile Model + Service
  ├── T10-08: ConnectionProfile ORM + repository
  └── T10-09: ConnectionService (CRUD + test + factory + Fernet)

Step 3: SettingsView Connections Tab
  ├── T10-10: Connections tab list panel
  └── T10-11: Add/Edit modal with inline test

Step 4: Import Wizard Extension (depends on Steps 1–2)
  ├── T10-12: Source Type selector in Step 1
  ├── T10-13: Database path — Step 1b + Step 2 table picker
  └── T10-14: ImportWizardService connector parameter

Step 5: Multi-Location ORM Layer (can run in parallel with Steps 2–4)
  ├── T10-15: Location ORM + repository
  ├── T10-16: ProductLocation ORM + repository
  └── T10-17: StockTransfer ORM + repository

Step 6: Multi-Location Services (depends on Step 5)
  ├── T10-18: LocationService
  └── T10-19: StockTransferService

Step 7: Location UI (depends on Steps 5–6)
  ├── T10-20: LocationsView
  ├── T10-21: StockTransferView
  ├── T10-22: InventoryView location filter
  ├── T10-23: Dashboard/Alerts/Executive location filter
  └── T10-24: App navigation wiring

Step 8: i18n + Packaging
  ├── T10-25: Locale .po updates + .mo recompile
  └── T10-26: PyInstaller spec update + .app smoke test

Step 9: Testing (can begin per group as Steps 1–6 complete)
  ├── T10-27: test_connector_framework.py          ← after Step 1
  ├── T10-28: test_connection_service.py           ← after Step 2
  ├── T10-29: test_location_service.py             ← after Step 6
  ├── T10-30: test_stock_transfer_service.py       ← after Step 6
  └── T10-31: test_multi_location_inventory.py     ← after Steps 5–6
```

---

## 10. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| `psycopg2-binary` or `PyMySQL` not available in test environment; CI fails on import | High | Low | All connector tests use `unittest.mock.patch` to mock driver-level `connect()` calls; actual DB connections are never made in the test suite; `requirements.txt` installs both packages unconditionally |
| `pyodbc` requires system ODBC driver; fails to import in CI and on end-user machines without ODBC | Medium | High | `GenericODBCConnector.__init__()` defers `import pyodbc` to method bodies and catches `ImportError`, raising a user-friendly message; `test_connector_framework.py` skips ODBC tests when `pyodbc` is not installed via `pytest.importorskip` |
| Fernet key rotation: if the user deletes `settings.json` or migrates to a new machine, `encrypted_password` values become unreadable | High | Low | `ConnectionService.get_connector()` catches `InvalidToken` from Fernet and raises `ConnectorError("Stored credentials are invalid — please re-enter the password")`; the UI shows this as a recoverable error prompting re-entry |
| `SELECT FOR UPDATE` not supported by SQLite (the app's storage backend) | High | Medium | SQLite supports `BEGIN EXCLUSIVE TRANSACTION`; `ProductLocationRepository.increment_reserved()` uses `session.execute(text("BEGIN EXCLUSIVE"))` before the update; tested with concurrent threads in `test_location_service.py::test_concurrent_reservation_no_oversell` |
| Location filter added to 4 views; forgetting to pass `location_id=None` default in service calls causes regressions in Phase 1–9 tests | Medium | Medium | `KPIService.get_kpis(location_id=None)`, `AlertService.get_active_alerts(location_id=None)` — `None` preserves existing aggregate behaviour; all Phase 1–9 tests pass `None` implicitly and are unaffected |
| Import Wizard database path: `list_tables()` on a slow remote DB blocks the Tkinter main thread | High | Medium | `list_tables()` called in a `threading.Thread`; result posted back to main thread via `App.after()` queue (same pattern as `SchedulerService`); Step 1b shows a spinner during the call |
| `StockTransferService.cancel()` for IN_TRANSIT transfers reverses already-dispatched stock, but the physical goods are still in transit — business process ambiguity | Low | Medium | Documented in `StockTransferView` tooltip: "Cancelling an IN-TRANSIT transfer records a stock reversal; ensure the physical shipment is returned or redirect it before cancelling"; MANAGER role required; AuditEvent records the cancellation |
| Multi-location stock data migrated from Phase 1–9 single-pool inventory: existing `Inventory` records have no `location_id` and cannot be assigned to `ProductLocation` automatically | Medium | Medium | On first launch after Phase 10 schema migration, `App._run_migrations()` creates a default `Location(name="Default Warehouse", code="DEFAULT", type="WAREHOUSE")` and inserts `ProductLocation` records mirroring existing `Inventory.current_stock` values; migration is idempotent |
| Phase 10 adds 2 new sidebar entries (Locations, Stock Transfers); total nav items grows to 14; sidebar may overflow on small screens | Low | Low | Sidebar uses `CTkScrollableFrame` since Phase 3; additional entries scroll naturally; minimum window height (640 px) documented in Phase 1 UI spec |

---

## 11. Testing Strategy

### 11.1 Connector Framework Tests (`tests/test_connector_framework.py`)

| Test | Validates |
|---|---|
| `test_csv_connector_list_tables_returns_filename` | `CSVConnector("/tmp/test.csv").list_tables()` returns `["test.csv"]` |
| `test_csv_connector_fetch_dataframe` | `CSVConnector.fetch_dataframe("test.csv")` returns correct DataFrame from temp file |
| `test_csv_connector_preserves_leading_zero_sku` | SKU column `"00123"` is not coerced to `123` by pandas |
| `test_sqlite_connector_list_tables` | `SQLiteConnector` with in-memory SQLite via temp file; `list_tables()` returns created table name |
| `test_sqlite_connector_fetch_dataframe` | `fetch_dataframe("test_table")` returns expected rows |
| `test_postgresql_connector_test_connection_returns_false_on_failure` | Patches `psycopg2.connect` to raise `OperationalError`; `test_connection()` returns `False`, not raises |
| `test_mysql_connector_list_tables_via_mock` | Patches `PyMySQL.connect`; `list_tables()` returns mocked cursor rows |
| `test_connector_error_wraps_driver_exception` | `PostgreSQLConnector.fetch_dataframe()` raises `ConnectorError` (not raw `psycopg2.OperationalError`) on mock failure |
| `test_generic_odbc_import_error_raises_connector_error` | When `pyodbc` is absent, `GenericODBCConnector.list_tables()` raises `ConnectorError` with message |
| `test_fetch_dataframe_limit_applied` | `SQLiteConnector.fetch_dataframe("t", limit=5)` returns at most 5 rows from a 20-row table |

### 11.2 Connection Service Tests (`tests/test_connection_service.py`)

| Test | Validates |
|---|---|
| `test_create_profile_requires_admin` | `create_profile(actor="viewer_user", ...)` raises `PermissionDeniedError` |
| `test_create_profile_encrypts_password` | Stored `encrypted_password` is not equal to plaintext |
| `test_fernet_round_trip` | `decrypt_password(encrypt_password("secret")) == "secret"` |
| `test_get_connector_returns_postgresql_instance` | `get_connector(profile(driver="POSTGRESQL"))` returns `PostgreSQLConnector` |
| `test_get_connector_returns_csv_instance` | `get_connector(profile(driver="CSV"))` returns `CSVConnector` |
| `test_test_connection_persists_result` | `test_connection()` updates `last_tested_at` and `last_test_ok` on the profile |
| `test_delete_profile_requires_admin` | Non-admin delete raises `PermissionDeniedError` |
| `test_invalid_fernet_token_raises_connector_error` | Corrupt `encrypted_password` in profile causes `get_connector()` to raise `ConnectorError` |

### 11.3 Location Service Tests (`tests/test_location_service.py`)

| Test | Validates |
|---|---|
| `test_create_location_requires_manager` | OPERATOR role raises `PermissionDeniedError` |
| `test_create_location_upcases_code` | `code="wh-01"` stored as `"WH-01"` |
| `test_create_location_invalid_type_raises` | `type_="AIRPORT"` raises `ValueError` |
| `test_get_stock_by_location_available_stock` | `available = current_stock - reserved_stock` computed correctly |
| `test_get_stock_by_location_no_stock_returns_empty` | Location with no `ProductLocation` records returns `[]` |
| `test_get_all_locations_summary_aggregate` | `total_stock` sums all `ProductLocation.current_stock` at the location |
| `test_deactivate_location_blocked_by_open_draft` | `deactivate_location()` raises `ValidationError` when open DRAFT transfers exist |
| `test_deactivate_location_blocked_by_in_transit` | Same check for IN_TRANSIT status |
| `test_move_stock_decrements_source_increments_dest` | Source `current_stock` decreases; destination `current_stock` increases by `qty` |
| `test_move_stock_creates_product_location_if_absent` | New `ProductLocation` row created for destination if no prior stock existed |

### 11.4 Stock Transfer Service Tests (`tests/test_stock_transfer_service.py`)

| Test | Validates |
|---|---|
| `test_create_draft_increments_reserved_stock` | `ProductLocation.reserved_stock` at source += qty after `create_draft()` |
| `test_create_draft_insufficient_available_raises` | Available = current − reserved < qty raises `InsufficientStockError` |
| `test_create_draft_same_location_raises` | `from_location_id == to_location_id` raises `ValueError` |
| `test_dispatch_decrements_current_and_reserved` | Source `current_stock -= qty`; `reserved_stock -= qty` |
| `test_dispatch_invalid_status_raises` | `dispatch()` on IN_TRANSIT transfer raises `InvalidTransitionError` |
| `test_receive_increments_destination_stock` | `to_location.current_stock += qty` after `receive()` |
| `test_receive_invalid_status_raises` | `receive()` on DRAFT transfer raises `InvalidTransitionError` |
| `test_cancel_draft_releases_reservation` | `from_location.reserved_stock -= qty` after `cancel()` on DRAFT |
| `test_cancel_in_transit_requires_manager` | OPERATOR role raises `PermissionDeniedError` for IN_TRANSIT cancel |
| `test_cancel_in_transit_rolls_back_source_stock` | `from_location.current_stock += qty` after MANAGER cancels IN_TRANSIT transfer |

### 11.5 Multi-Location Inventory Tests (`tests/test_multi_location_inventory.py`)

| Test | Validates |
|---|---|
| `test_inventory_service_location_filter` | `InventoryService.get_products(location_id=1)` returns only products with stock at location 1 |
| `test_alert_service_location_filter` | Low-stock alert fired for location 1 only when that location's `ProductLocation.current_stock < reorder_point` |
| `test_alert_all_locations_aggregates` | `AlertService.get_active_alerts(location_id=None)` checks total stock across all locations |
| `test_full_transfer_cycle_balances` | DRAFT → dispatch → receive: source loses qty, destination gains qty; total system stock unchanged |
| `test_cancelled_draft_balances` | DRAFT → cancel: reserved released; source `current_stock` unchanged |
| `test_kpi_service_location_total_value` | `KPIService.get_kpis(location_id=2)` returns only the stock value held at location 2 |
| `test_default_location_migration` | Schema migration creates "Default Warehouse" and migrates existing `Inventory.current_stock` to `ProductLocation` |

---

## 12. New i18n Strings (~80 total)

| Category | Count | Examples (EN) | PT-BR | ES |
|---|---|---|---|---|
| Connection management | 26 | "Connections", "Add Connection", "Test Connection", "Driver", "Host", "Port", "Database", "Username", "Password", "Connection String", "Connected", "Connection Failed", "Last Tested", "Never" | "Conexões", "Adicionar Conexão", "Testar Conexão", "Driver", "Servidor", "Porta", "Banco de Dados", "Usuário", "Senha", "String de Conexão", "Conectado", "Falha na Conexão", "Último Teste", "Nunca" | "Conexiones", "Agregar Conexión", "Probar Conexión", "Controlador", "Host", "Puerto", "Base de Datos", "Usuario", "Contraseña", "Cadena de Conexión", "Conectado", "Error de Conexión", "Última Prueba", "Nunca" |
| Location management | 20 | "Locations", "Add Location", "Location Code", "Location Type", "WAREHOUSE", "STORE", "DC", "Deactivate Location", "Total Stock", "SKU Count", "Available Stock", "Reserved" | "Localidades", "Adicionar Localidade", "Código", "Tipo", "ARMAZÉM", "LOJA", "CD", "Desativar Localidade", "Estoque Total", "Qtd. SKUs", "Estoque Disponível", "Reservado" | "Ubicaciones", "Agregar Ubicación", "Código", "Tipo", "ALMACÉN", "TIENDA", "CD", "Desactivar Ubicación", "Stock Total", "Cant. SKUs", "Stock Disponible", "Reservado" |
| Stock transfers | 24 | "Stock Transfers", "New Transfer", "From Location", "To Location", "Transfer Qty", "Dispatch", "Receive", "IN_TRANSIT", "RECEIVED", "Insufficient Stock", "Cancel Transfer", "Transfer Notes", "Dispatched", "Received At" | "Transferências", "Nova Transferência", "Origem", "Destino", "Quantidade", "Despachar", "Receber", "EM TRÂNSITO", "RECEBIDO", "Estoque Insuficiente", "Cancelar Transferência", "Notas", "Despachado", "Recebido em" | "Transferencias", "Nueva Transferencia", "Desde", "Hasta", "Cantidad", "Despachar", "Recibir", "EN TRÁNSITO", "RECIBIDO", "Stock Insuficiente", "Cancelar Transferencia", "Notas", "Despachado", "Recibido el" |
| Import source | 6 | "Browse File", "Database Connection", "Select Connection", "Select Table", "Source Type", "Refresh Tables" | "Selecionar Arquivo", "Conexão de Banco", "Selecionar Conexão", "Selecionar Tabela", "Tipo de Origem", "Atualizar Tabelas" | "Examinar Archivo", "Conexión de Base de Datos", "Seleccionar Conexión", "Seleccionar Tabla", "Tipo de Origen", "Actualizar Tablas" |
| Error messages | 4 | "Credentials invalid — please re-enter", "pyodbc not installed", "No tables found", "Location has open transfers" | "Credenciais inválidas — re-insira", "pyodbc não instalado", "Nenhuma tabela encontrada", "Localidade possui transferências abertas" | "Credenciales inválidas — vuelva a ingresarlas", "pyodbc no instalado", "No se encontraron tablas", "La ubicación tiene transferencias abiertas" |
| **Total** | **~80** | | | |

---

## 13. Non-Functional Requirements (Phase 10)

| Requirement | Target | Validation Method |
|---|---|---|
| `test_connection()` background thread response time | Completes or times out within `CONNECTOR_TEST_TIMEOUT_S` (5 s) | Manual test against a reachable PostgreSQL instance; UI shows spinner with timeout badge |
| `list_tables()` call (Step 1b background thread) | UI spinner shown immediately; result populates within 10 s on typical LAN | Manual smoke test against local PostgreSQL |
| `StockTransferService.create_draft()` — concurrent reservation | No oversell when two threads reserve from the same location simultaneously | `test_concurrent_reservation_no_oversell` test with two threads |
| Location filter impact on existing view load time | < 200 ms additional latency for `location_id != None` queries (indexed FK joins) | `pytest-benchmark` on `LocationService.get_stock_by_location()` with 500 products |
| `tools/extract_strings.py --check-completeness` after Phase 10 strings added | Exit code 0; all 3 locales complete | Run as part of Phase 10 completion verification |
| No regression in existing 389 Phase 1–9 tests | `389 passed` | Full `pytest` run after every implementation step |
| Binary size increase (Phase 10 deps in `.app`) | ≤ +20 MB (psycopg2-binary + PyMySQL + cryptography) | `du -sh dist/LogisticsDSS.app` after rebuild |
| Non-GUI test coverage | ≥ 90% | `pytest --cov=src --ignore=src/ui` |

---

## 14. Phase 10 Exit Criteria

- [ ] `CSVConnector.fetch_dataframe()` preserves leading-zero SKU values (`test_csv_connector_preserves_leading_zero_sku`)
- [ ] `PostgreSQLConnector.test_connection()` returns `False` (not raises) when the host is unreachable (`test_postgresql_connector_test_connection_returns_false_on_failure`)
- [ ] `ConnectionService.encrypt_password()` / `decrypt_password()` Fernet round-trip is lossless (`test_fernet_round_trip`)
- [ ] `ConnectionService.create_profile()` raises `PermissionDeniedError` for non-ADMIN actors (`test_create_profile_requires_admin`)
- [ ] `ConnectionService.get_connector()` returns the correct concrete subclass for each `driver` value (`test_get_connector_returns_postgresql_instance`, `test_get_connector_returns_csv_instance`)
- [ ] `StockTransferService.create_draft()` increments `reserved_stock` at the source location and raises `InsufficientStockError` when available stock is insufficient (`test_create_draft_increments_reserved_stock`, `test_create_draft_insufficient_available_raises`)
- [ ] Full DRAFT → dispatch → receive cycle: source `current_stock` decreases by `qty`; destination `current_stock` increases by `qty`; total system stock is conserved (`test_full_transfer_cycle_balances`)
- [ ] Cancelling an IN_TRANSIT transfer requires MANAGER role; source `current_stock` is restored (`test_cancel_in_transit_requires_manager`, `test_cancel_in_transit_rolls_back_source_stock`)
- [ ] `LocationService.deactivate_location()` is blocked when DRAFT or IN_TRANSIT transfers exist (`test_deactivate_location_blocked_by_open_draft`, `test_deactivate_location_blocked_by_in_transit`)
- [ ] `InventoryView` location filter changes the data table to show only stock held at the selected location; "All Locations" restores the aggregate view (`test_inventory_service_location_filter`)
- [ ] Schema migration creates "Default Warehouse" and migrates existing `Inventory.current_stock` values to `ProductLocation` on first Phase 10 launch (`test_default_location_migration`)
- [ ] `tools/extract_strings.py --check-completeness` reports `[pt_BR] Complete ✓` and `[es] Complete ✓` after Phase 10 locale additions
- [ ] PyInstaller `.app` correctly imports `psycopg2`, `PyMySQL`, and `cryptography.fernet`; smoke test: create a PostgreSQL connection profile, test it, and perform a database import within the bundled app
- [ ] `GenericODBCConnector` raises a user-readable `ConnectorError` (not an unhandled `ImportError`) when `pyodbc` is not installed
- [ ] All 45 new Phase 10 tests pass; total test count = 434; 0 regressions in Phase 1–9 tests
- [ ] Non-GUI test coverage remains ≥ 90%

---

## 15. Transition to Phase 11

Phase 10 delivers ERP database integration and multi-location inventory management. The remaining roadmap items identified at project initiation are:

**Phase 11 candidates:**

1. **Mobile Companion API:**
   A lightweight `FastAPI` layer (`src/api/`) exposes read-only JSON endpoints backed by existing services: `GET /api/v1/kpis` (KPIService), `GET /api/v1/alerts` (AlertService), `GET /api/v1/transfers` (StockTransferService). An ADMIN-only API token field (`api_token: str`) is added to the `User` ORM model; token-based authentication (Bearer scheme, `itsdangerous` HMAC) gates all API endpoints. A `uvicorn` server is started as a background thread by `App.__init__()` alongside the existing Tkinter event loop. The Phase 8 `APScheduler` infrastructure is extended to push a nightly KPI snapshot to a configurable webhook URL (stored in `SettingsService`). Phase 10's `TranslationService` observer pattern is adopted by the API layer's error response messages.

2. **Real-Time Push Notifications:**
   The Phase 8 `App.after(2000, _poll_scheduler_queue)` polling pattern is replaced by a WebSocket connection to the Phase 11 FastAPI server. Low-stock threshold breaches (Phase 3), new PO approvals (Phase 7), and overdue scheduled reports (Phase 8) push toast notifications to the Tkinter UI without polling. A `NotificationService` manages WebSocket client connections and routes events from APScheduler jobs to connected desktop clients.

3. **Containerization and PostgreSQL Migration:**
   A `docker-compose.yml` provides a one-command development environment: the Logistics DSS desktop app as a service mounting the host display (Linux X11/XWayland) or running headlessly with the Phase 11 API, a PostgreSQL container replacing the SQLite backend, and a pgAdmin container. The `DatabaseManager` connection string is made configurable via `LOGISTICS_DSS_DB_URL` environment variable, enabling PostgreSQL as the production backend while retaining SQLite for local development. Phase 10's connector framework (`PostgreSQLConnector`) handles the app's own PostgreSQL connection when this variable is set.

**Prerequisites from Phase 10 used by Phase 11:**
- `ConnectionService.get_connector()` factory reused to back the FastAPI data endpoints with the same connection profiles saved in `SettingsView`
- `StockTransferService` state-change events (`STOCK_TRANSFER_DISPATCHED`, `STOCK_TRANSFER_RECEIVED`) become WebSocket push events in Phase 11
- `ProductLocation` and `Location` data exposed via Phase 11 API for mobile consumption
- `cryptography` package already installed (Phase 10 dependency) — reused by Phase 11 for API token generation (`cryptography.hazmat.primitives.kdf.pbkdf2`)

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-02-26 | Initial Phase 10 implementation plan |

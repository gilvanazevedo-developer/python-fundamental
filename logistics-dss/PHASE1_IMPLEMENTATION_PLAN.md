# Logistics DSS - Phase 1 Implementation Plan
# Core Data Layer

**Project:** Logistics Decision Support System
**Phase:** 1 of 8 - Core Data Layer
**Author:** Gilvan de Azevedo
**Date:** 2026-02-12
**Status:** In Progress

---

## 1. Phase 1 Objective

Build the foundational data layer that enables CSV/Excel import, local SQLite storage, and robust data validation. This phase establishes the data backbone upon which all subsequent phases (dashboards, analytics, forecasting) will depend.

**Deliverables:**
- CSV and Excel file import capability
- Local SQLite database with full schema
- Data validation engine with configurable rules
- Import audit logging
- Centralized configuration and logging infrastructure

---

## 2. Architecture Overview

```
logistics-dss/
├── config/
│   ├── __init__.py
│   ├── constants.py          # Business constants, enums, validation rules
│   └── settings.py           # Application settings (paths, limits, toggles)
├── data/
│   ├── database/             # SQLite database files
│   ├── exports/              # Export output directory
│   └── imports/              # Import staging directory
├── src/
│   ├── __init__.py
│   ├── logger.py             # Centralized logging with rotation
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py     # DatabaseManager (singleton, session lifecycle)
│   │   └── models.py         # SQLAlchemy ORM models
│   ├── importer/
│   │   ├── __init__.py
│   │   ├── base.py           # BaseImporter (abstract, shared logic)
│   │   ├── csv_importer.py   # CSVImporter (encoding detection, type conversion)
│   │   └── excel_importer.py # ExcelImporter (multi-sheet support)
│   ├── utils/
│   │   └── __init__.py
│   └── validator/
│       ├── __init__.py
│       ├── data_validator.py # DataValidator (row and DataFrame validation)
│       └── rules.py          # Validation rule classes (Required, Range, etc.)
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures and helpers
│   ├── test_database.py      # Database model and connection tests
│   ├── test_importer.py      # CSV/Excel importer tests
│   └── test_validator.py     # Validation rule and engine tests
├── logs/                     # Application log files
├── .env                      # Environment variables
├── .env.example              # Environment template
├── .gitignore
├── requirements.txt          # Phase 1 dependencies
└── PROJECT_REQUIREMENTS.md   # Full project requirements
```

---

## 3. Component Design

### 3.1 Database Layer

**Technology:** SQLAlchemy 2.0 ORM + SQLite

**Schema (6 tables):**

| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `products` | SKU master data (name, category, cost, price) | `id` (String) |
| `warehouses` | Location master data (name, location, capacity) | `id` (String) |
| `suppliers` | Supplier data (lead time, min order qty) | `id` (String) |
| `inventory_levels` | Current stock by product + warehouse | `id` (Auto-increment) |
| `sales_records` | Historical sales transactions | `id` (Auto-increment) |
| `import_logs` | Audit trail for all import operations | `id` (Auto-increment) |

**Key Design Decisions:**
- **Singleton DatabaseManager** -- single engine instance avoids connection pool issues with SQLite
- **Context-managed sessions** -- automatic commit/rollback via `get_session()` context manager
- **Foreign key enforcement** -- enabled via SQLite PRAGMA on every connection
- **Upsert behavior** -- `session.merge()` used for imports to handle re-imports gracefully
- **Check constraints** -- database-level enforcement for non-negative costs, quantities, and capacities

**Entity Relationships:**
```
Products ──┬── InventoryLevels (product_id FK)
            └── SalesRecords    (product_id FK)

Warehouses ─┬── InventoryLevels (warehouse_id FK)
             └── SalesRecords    (warehouse_id FK)

InventoryLevels: unique index on (product_id, warehouse_id)
SalesRecords:    composite indexes on (date, product_id) and (date, warehouse_id)
```

### 3.2 Import Layer

**Supported formats:** CSV (.csv), Excel (.xlsx, .xls)

**Import Pipeline:**
```
File Selection
    │
    ▼
File Validation (exists, readable, supported extension)
    │
    ▼
File Reading (encoding detection for CSV, engine selection for Excel)
    │
    ▼
Column Normalization (lowercase, strip whitespace)
    │
    ▼
Column Validation (check required columns present)
    │
    ▼
Row-by-Row Data Validation (type checks, range checks, required fields)
    │
    ▼
Type Conversion (strings → Decimal, int, date, datetime)
    │
    ▼
Database Persistence (merge/upsert per record)
    │
    ▼
Import Logging (audit trail in import_logs table)
    │
    ▼
ImportResult (success/failure summary, error details, duration)
```

**CSV Importer Features:**
- Auto-detection of file encoding (UTF-8, Latin-1, CP1252, ISO-8859-1)
- All columns read as strings initially, then type-converted after validation
- Multiple date format support (ISO, DD/MM/YYYY, MM/DD/YYYY)
- NA value handling (empty, "NA", "N/A", "null", "NULL", "None")

**Excel Importer Features:**
- Engine auto-selection: `openpyxl` for .xlsx, `xlrd` for .xls
- Single-sheet or multi-sheet import
- Sheet name listing for user selection
- Inherits all CSV validation and persistence logic

**Import Result Tracking:**
- `ImportResult` dataclass captures: success/failure, record counts, errors, warnings, duration
- Every import logged to `import_logs` table with status (success/partial/failed)

### 3.3 Validation Engine

**Architecture:** Rule-based pattern with composable validators

**Rule Hierarchy:**
```
ValidationRule (abstract base)
├── RequiredRule         -- field must not be null or empty
├── StringLengthRule     -- max character limit per field
├── NumericRangeRule     -- min/max bounds for numeric fields
├── DecimalRule          -- must parse as valid Decimal
├── IntegerRule          -- must parse as whole number
├── DateRule             -- must match known date formats
├── DateTimeRule         -- must match known datetime formats
├── PatternRule          -- must match regex pattern
└── UniqueRule           -- must not duplicate existing values
```

**Validation Configuration (from `constants.py`):**

| Field | Type | Range |
|-------|------|-------|
| `unit_cost` | Decimal | 0 - 1,000,000 |
| `unit_price` | Decimal | 0 - 1,000,000 |
| `quantity` | Integer | 0 - 10,000,000 |
| `quantity_sold` | Integer | 0 - 10,000,000 |
| `revenue` | Decimal | 0 - 100,000,000 |
| `lead_time_days` | Integer | 0 - 365 |
| `min_order_qty` | Integer | 1 - 1,000,000 |
| `capacity` | Integer | 1 - 100,000,000 |

**String Length Limits:**

| Field | Max Length |
|-------|-----------|
| `id`, `product_id`, `warehouse_id` | 50 |
| `name` | 200 |
| `category` | 100 |
| `location` | 300 |

**Validation Behavior:**
- Row-level validation: stops checking a field after first error (fail-fast per field)
- DataFrame validation: collects up to `MAX_VALIDATION_ERRORS` (default 100) then stops
- Valid rows are separated into a clean DataFrame for import; invalid rows are reported
- Validation summary aggregates errors by field for diagnostic reporting

### 3.4 Configuration & Logging

**Settings (`config/settings.py`):**
- Paths derived from project root using `pathlib.Path`
- Environment overrides via `.env` (database name, log level, strict validation)
- Directory auto-creation on import
- Configurable limits: max file size (50 MB), batch size (1000), max validation errors (100)

**Logging (`src/logger.py`):**
- Dual output: console (stdout) + rotating file handler
- Log rotation: 5 MB max per file, 3 backups retained
- `LoggerMixin` class for easy integration into any component
- `log_function_call` decorator for tracing entry/exit of functions

---

## 4. Data Types Supported

| Data Type | Required Columns | Description |
|-----------|-----------------|-------------|
| **Products** | id, name, category, unit_cost, unit_price | SKU master catalog |
| **Inventory** | product_id, warehouse_id, quantity, last_updated | Current stock levels |
| **Sales** | date, product_id, warehouse_id, quantity_sold, revenue | Historical transactions |
| **Suppliers** | id, name, lead_time_days, min_order_qty | Supplier master data |
| **Warehouses** | id, name, location, capacity | Location/facility data |

---

## 5. Technology Stack (Phase 1)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Language | Python | 3.12 | Runtime |
| ORM | SQLAlchemy | >= 2.0.0 | Database abstraction |
| Database | SQLite | Built-in | Embedded local storage |
| Data Processing | Pandas | >= 2.0.0 | DataFrame operations |
| Excel Support | openpyxl | >= 3.1.0 | .xlsx file reading |
| Environment | python-dotenv | >= 1.0.0 | .env file loading |
| Testing | pytest | >= 8.0.0 | Test framework |
| Coverage | pytest-cov | >= 4.0.0 | Code coverage reporting |
| Formatting | black | >= 23.0.0 | Code formatting |
| Import Sort | isort | >= 5.12.0 | Import ordering |
| Type Checking | mypy | >= 1.0.0 | Static type analysis |

---

## 6. Implementation Tasks

### 6.1 Completed

| # | Task | Module | Status |
|---|------|--------|--------|
| 1 | Define project directory structure | Root | Done |
| 2 | Create settings module with path management | `config/settings.py` | Done |
| 3 | Define business constants and enums | `config/constants.py` | Done |
| 4 | Implement SQLAlchemy ORM models (6 tables) | `src/database/models.py` | Done |
| 5 | Implement DatabaseManager (singleton, sessions) | `src/database/connection.py` | Done |
| 6 | Build centralized logging with rotation | `src/logger.py` | Done |
| 7 | Implement validation rule classes (8 rules) | `src/validator/rules.py` | Done |
| 8 | Build DataValidator with row/DataFrame validation | `src/validator/data_validator.py` | Done |
| 9 | Implement BaseImporter (abstract, pipeline) | `src/importer/base.py` | Done |
| 10 | Implement CSVImporter (encoding, type conversion) | `src/importer/csv_importer.py` | Done |
| 11 | Implement ExcelImporter (multi-sheet) | `src/importer/excel_importer.py` | Done |
| 12 | Create test fixtures and conftest | `tests/conftest.py` | Done |
| 13 | Write database model tests | `tests/test_database.py` | Done |
| 14 | Write importer tests (unit + integration) | `tests/test_importer.py` | Done |
| 15 | Write validation rule tests | `tests/test_validator.py` | Done |
| 16 | Set up requirements.txt | Root | Done |
| 17 | Configure environment variables (.env) | Root | Done |

### 6.2 Remaining

| # | Task | Priority | Description |
|---|------|----------|-------------|
| 18 | Add data export capability (CSV/Excel) | Medium | Export query results and reports to file |
| 19 | Implement batch import for large files | Medium | Process records in configurable batch sizes (BATCH_SIZE=1000) |
| 20 | Add file size validation pre-import | Low | Reject files exceeding MAX_FILE_SIZE_MB (50 MB) |
| 21 | Create CLI entry point for imports | Medium | Command-line interface for manual import operations |
| 22 | Add database migration support | Low | Schema versioning for future updates (Alembic) |
| 23 | Increase test coverage to 90%+ | Medium | Edge cases, error paths, concurrent access |
| 24 | Add type hints verification with mypy | Low | Ensure static type consistency |

---

## 7. Test Coverage Summary

| Module | Test File | Test Classes | Test Count |
|--------|-----------|-------------|------------|
| Database Models | `test_database.py` | 7 classes | 8 tests |
| Database Manager | `test_database.py` | 1 class | 3 tests |
| CSV Importer | `test_importer.py` | 1 class | 7 tests |
| Excel Importer | `test_importer.py` | 1 class | 3 tests |
| Integration | `test_importer.py` | 1 class | 2 tests |
| ImportResult | `test_importer.py` | 1 class | 3 tests |
| Validation Rules | `test_validator.py` | 7 classes | 18 tests |
| DataValidator | `test_validator.py` | 1 class | 4 tests |
| **Total** | **4 files** | **19 classes** | **48 tests** |

**Testing Strategy:**
- Unit tests: isolated component testing with mocks for external dependencies
- Integration tests: full import pipeline with real SQLite database (temp files)
- Fixtures: shared sample data (products, inventory, sales, warehouses, suppliers)
- Cleanup: temporary directories and databases auto-removed after tests

---

## 8. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large file imports cause memory issues | High | Batch processing (Task #19), file size limits |
| Date format ambiguity (DD/MM vs MM/DD) | Medium | Multiple format parsing with priority ordering |
| Encoding issues with international data | Medium | Multi-encoding fallback (5 encodings supported) |
| SQLite concurrency limitations | Low | Single-user desktop app; thread safety via singleton |
| Schema changes break existing data | Medium | Future Alembic migration support (Task #22) |

---

## 9. Phase 1 Exit Criteria

- [x] All 5 data types can be imported from CSV files
- [x] All 5 data types can be imported from Excel files
- [x] Data validation catches invalid records and reports errors
- [x] Valid records are persisted to SQLite with referential integrity
- [x] Import operations are logged with audit trail
- [x] All existing tests pass
- [ ] Test coverage reaches 90%+
- [ ] CLI entry point available for manual imports
- [ ] Data export to CSV/Excel functional

---

## 10. Transition to Phase 2

Phase 2 (Basic Dashboard) will build on the data layer by:

1. **Reading from SQLite** -- querying products, inventory, and sales via SQLAlchemy sessions
2. **Computing KPIs** -- stock levels, days of supply, turnover rates from persisted data
3. **Rendering UI** -- CustomTkinter desktop interface with tables and summary panels
4. **Data refresh** -- triggering re-import or re-query from the dashboard

**Prerequisites from Phase 1:**
- Stable database schema (no breaking changes expected)
- Working import pipeline for populating test data
- Validation engine ensuring data quality for KPI calculations

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-12 | Initial Phase 1 implementation plan |
| 1.1 | 2026-02-19 | Updated with implementation status and remaining tasks |

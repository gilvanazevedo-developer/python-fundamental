# Logistics DSS - Phase 7 Implementation Plan
# Supplier & Purchase Order Management

**Project:** Logistics Decision Support System
**Phase:** 7 of 8 — Supplier & Purchase Order Management
**Author:** Gilvan de Azevedo
**Date:** 2026-02-20
**Status:** Not Started
**Depends on:** Phase 6 (Executive Dashboard & Reporting) — functionally complete

---

## 1. Phase 7 Objective

Extend the Logistics DSS from a pure analytical tool into an operational procurement platform. Phase 7 introduces supplier master data, a full purchase order lifecycle (DRAFT → SUBMITTED → CONFIRMED → RECEIVED), and supplier reliability scoring. The Phase 5 inventory policy engine's `suggested_order_qty` values become actionable: a buyer can convert any STOCKOUT or BELOW_ROP alert directly into a draft purchase order with a single click, review and confirm it, and later record the actual receipt — closing the loop between the analytical recommendation and the physical replenishment event.

Two new UI views (Suppliers, Purchase Orders) give buyers a structured workspace for procurement activities. The Executive Dashboard gains a Procurement section showing open PO value, supplier on-time delivery rate, and pending order count. The safety stock formula is extended to account for lead-time variability: `SS = z × √(L̄ × σ_d² + D̄² × σ_L²)`, improving policy accuracy for suppliers with inconsistent delivery schedules.

**Deliverables:**
- `Supplier` ORM model: master data, default lead time, lead time standard deviation, reliability score
- `PurchaseOrder` ORM model: full lifecycle from DRAFT to RECEIVED with quantity and pricing
- `SupplierPerformanceRecord` ORM model: per-PO delivery measurement feeding rolling reliability scores
- `SupplierRepository` and `PurchaseOrderRepository`: clean query layer for all procurement data
- `SupplierService`: CRUD, reliability score computation, lead-time statistics
- `PurchaseOrderService`: CRUD, PO draft generation from alert + policy, receipt confirmation workflow
- Extended `OptimizationService`: lead-time-variance safety stock formula (optional per supplier)
- Extended `KPIService`: 4 new procurement headline KPIs
- `SuppliersView`: supplier list, add/edit modal, reliability sparkline, PO history per supplier
- `PurchaseOrdersView`: full PO pipeline table, status filter, receive-PO modal with partial-receipt support
- `AlertsView` extension: "Create PO Draft" action button on replenishment alerts
- `OptimizationView` extension: supplier selector per product, lead-time std display
- `ExecutiveView` extension: Procurement section (open PO value, on-time rate, pending orders)
- Full test suite (51 new tests): repositories, services, reliability scoring, PO generation, extended SS formula

---

## 2. Phase 6 Dependencies (Available)

Phase 7 builds directly on the following Phase 6 (and prior) components:

| Component | Module | Usage in Phase 7 |
|---|---|---|
| `ReportLog` ORM | `src/database/models.py` | PO receipt events logged via same audit pattern |
| `ReportRunner` | `src/reporting/report_runner.py` | POLICY report gains "Purchase Orders" section once Phase 7 data exists |
| `ReportService` | `src/services/report_service.py` | Extended with `get_open_po_summary()` and `get_supplier_performance()` |
| `InventoryPolicy` ORM | `src/database/models.py` | `suggested_order_qty` drives PO draft quantity; `lead_time_days` mapped to `Supplier.default_lead_time_days` |
| `ReplenishmentAlert` ORM | `src/database/models.py` | STOCKOUT and BELOW_ROP alerts gain FK to `PurchaseOrder.id` (optional, set when PO generated) |
| `OptimizationRun` ORM | `src/database/models.py` | POs linked to the optimization run that recommended them |
| `OptimizationService` | `src/services/optimization_service.py` | Extended with lead-time-variance SS formula using `Supplier.lead_time_std_days` |
| `KPIService` | `src/services/kpi_service.py` | Extended with 4 procurement KPIs |
| `AlertsView` | `src/ui/views/alerts_view.py` | Extended: "Create PO Draft →" button on qualifying alerts |
| `OptimizationView` | `src/ui/views/optimization_view.py` | Extended: supplier selector per product row |
| `ExecutiveView` | `src/ui/views/executive_view.py` | Extended: Procurement section (Section E) |
| `DataTable` | `src/ui/widgets/data_table.py` | Supplier list, PO pipeline table, PO history per supplier |
| `ChartPanel` | `src/ui/widgets/chart_panel.py` | Reliability sparkline in SuppliersView; PO value bar chart |
| `KPICard` | `src/ui/widgets/kpi_card.py` | Procurement KPIs in ExecutiveView Procurement section |
| Constants | `config/constants.py` | Extended with PO status codes, reliability window, PO number format |
| `LoggerMixin` | `src/logger.py` | Logging in all new procurement modules |
| `DatabaseManager` | `src/database/connection.py` | Session handling for all new repositories |

---

## 3. Architecture Overview

### 3.1 Phase 7 Directory Structure

```
logistics-dss/
├── config/
│   └── constants.py            # + PO status codes, reliability constants, PO number format
├── src/
│   ├── database/
│   │   └── models.py           # + Supplier, PurchaseOrder, SupplierPerformanceRecord ORM models
│   ├── repositories/
│   │   ├── supplier_repository.py          # NEW: CRUD + reliability queries
│   │   └── purchase_order_repository.py    # NEW: PO CRUD + status-filter queries
│   ├── services/
│   │   ├── supplier_service.py             # NEW: CRUD + reliability scoring + lead-time stats
│   │   ├── purchase_order_service.py       # NEW: PO CRUD + draft generation + receipt workflow
│   │   ├── optimization_service.py         # (existing) + lead-time-variance SS formula
│   │   ├── kpi_service.py                  # (existing) + 4 procurement KPIs
│   │   └── report_service.py               # (existing) + open PO summary + supplier performance
│   └── ui/
│       ├── app.py                          # + Suppliers + Purchase Orders nav buttons
│       └── views/
│           ├── suppliers_view.py           # NEW: supplier list + add/edit modal + reliability chart
│           ├── purchase_orders_view.py     # NEW: PO pipeline + receive-PO modal
│           ├── alerts_view.py              # (existing) + "Create PO Draft" action button
│           ├── optimization_view.py        # (existing) + supplier selector per product
│           └── executive_view.py           # (existing) + Procurement KPIs section
├── tests/
│   ├── test_supplier_repository.py         # NEW: 7 tests
│   ├── test_po_repository.py               # NEW: 8 tests
│   ├── test_supplier_service.py            # NEW: 8 tests
│   ├── test_purchase_order_service.py      # NEW: 9 tests
│   ├── test_supplier_reliability.py        # NEW: 7 tests
│   ├── test_po_generation.py               # NEW: 6 tests
│   └── test_extended_ss_formula.py         # NEW: 6 tests
└── main.py                                 # (existing)
```

### 3.2 Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                             Presentation Layer                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ │
│  │Dashboard│ │Forecast │ │Optimiz. │ │ Alerts  │ │Executive │ │Reports  │ │
│  │  View   │ │  View   │ │View (+) │ │View (+) │ │View (+)  │ │  View   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘ └─────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │    NEW Views                                                             │ │
│  │    SuppliersView (NEW)          PurchaseOrdersView (NEW)                │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                              Service Layer                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │ Supplier     │  │ PurchaseOrder│  │Optimization│  │  KPI Service (+)  │  │
│  │ Service (NEW)│  │ Service (NEW)│  │ Service (+)│  │  Report Svc (+)   │  │
│  └──────────────┘  └──────────────┘  └────────────┘  └───────────────────┘  │
├──────────────────────────────────────────────────────────────────────────────┤
│                            Repository Layer                                    │
│  ┌──────────────────┐  ┌──────────────────────────┐                          │
│  │SupplierRepository│  │ PurchaseOrderRepository   │                          │
│  │    (NEW)         │  │         (NEW)             │                          │
│  └──────────────────┘  └──────────────────────────┘                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                         ORM / Database Layer                                   │
│  ┌────────────┐  ┌──────────────────┐  ┌───────────────────────────────────┐ │
│  │  Supplier  │  │  PurchaseOrder   │  │  SupplierPerformanceRecord (NEW)   │ │
│  │   (NEW)    │  │     (NEW)        │  │                                    │ │
│  └────────────┘  └──────────────────┘  └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Database Models

#### 4.1.1 `Supplier`

```python
class Supplier(Base):
    __tablename__ = "supplier"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    name                   = Column(String(128), nullable=False, unique=True)
    contact_name           = Column(String(128), nullable=True)
    email                  = Column(String(256), nullable=True)
    phone                  = Column(String(32),  nullable=True)
    address                = Column(Text,         nullable=True)
    default_lead_time_days = Column(Integer,      nullable=False, default=7)
    lead_time_std_days     = Column(Float,        nullable=False, default=0.0)
    # std dev of lead time in days — sourced from SupplierPerformanceRecord history
    # used in extended SS formula:  SS = z × sqrt(L̄ × σ_d² + D̄² × σ_L²)
    reliability_score      = Column(Float,        nullable=True)
    # fraction of on-time deliveries over SUPPLIER_RELIABILITY_WINDOW_DAYS; recomputed on each receipt
    active                 = Column(Boolean,      nullable=False, default=True)
    notes                  = Column(Text,         nullable=True)
    created_at             = Column(DateTime,     nullable=False, default=datetime.utcnow)
    updated_at             = Column(DateTime,     nullable=False, default=datetime.utcnow,
                                                  onupdate=datetime.utcnow)

    purchase_orders        = relationship("PurchaseOrder", back_populates="supplier")
    performance_records    = relationship("SupplierPerformanceRecord", back_populates="supplier")
```

**Indexes:**
- `(name)` — UNIQUE (already enforced by constraint)
- `(active, name)` — active supplier list sorted alphabetically
- `(reliability_score DESC)` — supplier ranking by performance

---

#### 4.1.2 `PurchaseOrder`

```python
class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id                   = Column(Integer,  primary_key=True, autoincrement=True)
    po_number            = Column(String(20), nullable=False, unique=True)
    # Format: PO-YYYYMMDD-NNNN (e.g. "PO-20260220-0001")

    supplier_id          = Column(Integer, ForeignKey("supplier.id"),    nullable=False)
    product_id           = Column(Integer, ForeignKey("product.id"),     nullable=False)
    optimization_run_id  = Column(Integer, ForeignKey("optimization_run.id"), nullable=True)
    alert_id             = Column(Integer, ForeignKey("replenishment_alert.id"), nullable=True)
    # alert_id: the replenishment alert that triggered this PO (if generated from an alert)

    status               = Column(String(16), nullable=False, default="DRAFT")
    # DRAFT → SUBMITTED → CONFIRMED → RECEIVED | CANCELLED

    ordered_qty          = Column(Integer, nullable=False)
    unit_price           = Column(Float,   nullable=True)
    total_value          = Column(Float,   nullable=True)
    # total_value = ordered_qty × unit_price; NULL if unit_price not set

    ordered_at           = Column(DateTime, nullable=True)   # set on SUBMITTED
    expected_arrival     = Column(DateTime, nullable=True)   # supplier-confirmed date (CONFIRMED)
    received_at          = Column(DateTime, nullable=True)   # set on RECEIVED
    actual_qty_received  = Column(Integer,  nullable=True)   # may differ from ordered_qty (partial)
    lead_time_actual_days = Column(Integer, nullable=True)
    # computed as (received_at - ordered_at).days on RECEIVED

    notes                = Column(Text,    nullable=True)
    created_at           = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at           = Column(DateTime, nullable=False, default=datetime.utcnow,
                                            onupdate=datetime.utcnow)

    supplier             = relationship("Supplier",             back_populates="purchase_orders")
    product              = relationship("Product")
    optimization_run     = relationship("OptimizationRun")
    alert                = relationship("ReplenishmentAlert")
    performance_record   = relationship("SupplierPerformanceRecord", back_populates="purchase_order",
                                        uselist=False)
```

**Indexes:**
- `(po_number)` — UNIQUE
- `(supplier_id, status)` — POs by supplier and current state
- `(product_id, status)` — open POs for a product
- `(status, ordered_at DESC)` — pipeline view ordered by recency
- `(optimization_run_id)` — POs generated from a specific optimization run

---

#### 4.1.3 `SupplierPerformanceRecord`

```python
class SupplierPerformanceRecord(Base):
    __tablename__ = "supplier_performance_record"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id      = Column(Integer, ForeignKey("supplier.id"),      nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_order.id"), nullable=False, unique=True)

    measured_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    promised_days    = Column(Integer,  nullable=False)   # default_lead_time_days at time of order
    actual_days      = Column(Integer,  nullable=False)   # lead_time_actual_days from PO
    on_time          = Column(Boolean,  nullable=False)   # actual_days <= promised_days
    qty_fill_rate    = Column(Float,    nullable=False)
    # actual_qty_received / ordered_qty; 1.0 = perfect; < 1.0 = short shipment

    supplier         = relationship("Supplier",      back_populates="performance_records")
    purchase_order   = relationship("PurchaseOrder", back_populates="performance_record")
```

**Indexes:**
- `(supplier_id, measured_at DESC)` — recent performance records per supplier
- `(on_time, supplier_id)` — on-time filtering for reliability score computation

---

### 4.2 Repository Layer

#### 4.2.1 `SupplierRepository` (`src/repositories/supplier_repository.py`)

| Method | Returns | Description |
|---|---|---|
| `get_all(active_only=True)` | `list[Supplier]` | All suppliers, optionally filtered to `active=True`; ordered by `name ASC` |
| `get_by_id(supplier_id)` | `Supplier \| None` | Single supplier by PK |
| `get_by_name(name)` | `Supplier \| None` | Case-insensitive exact match |
| `create(name, default_lead_time_days, **kwargs)` | `Supplier` | Insert and commit; raises `IntegrityError` on duplicate name |
| `update(supplier_id, **fields)` | `Supplier \| None` | Partial update; updates `updated_at` |
| `deactivate(supplier_id)` | `bool` | Sets `active=False`; returns False if not found |
| `get_performance_records(supplier_id, days=180)` | `list[SupplierPerformanceRecord]` | Records within last `days` calendar days |
| `get_lead_time_statistics(supplier_id)` | `tuple[float, float]` | `(mean_days, std_days)` from all closed POs |

---

#### 4.2.2 `PurchaseOrderRepository` (`src/repositories/purchase_order_repository.py`)

| Method | Returns | Description |
|---|---|---|
| `get_all(status=None, limit=100)` | `list[PurchaseOrder]` | All POs; filtered by `status` if provided; ordered by `ordered_at DESC NULLS LAST, created_at DESC` |
| `get_by_id(po_id)` | `PurchaseOrder \| None` | Single PO by PK; eager-loads supplier and product |
| `get_by_po_number(po_number)` | `PurchaseOrder \| None` | Unique lookup |
| `get_open_for_product(product_id)` | `list[PurchaseOrder]` | POs with `status IN (DRAFT, SUBMITTED, CONFIRMED)` for a product |
| `get_by_supplier(supplier_id, status=None)` | `list[PurchaseOrder]` | POs for a supplier, optionally filtered by status |
| `create(**fields)` | `PurchaseOrder` | Auto-generates `po_number`; inserts and commits |
| `update_status(po_id, new_status, **extra_fields)` | `PurchaseOrder \| None` | Status transition; sets `ordered_at`, `received_at` timestamps as appropriate |
| `get_total_open_value()` | `float` | SUM of `total_value` for all SUBMITTED/CONFIRMED POs |
| `get_next_po_sequence(date_str)` | `int` | Queries MAX sequence for `PO-{date_str}-NNNN`; returns next integer |

---

### 4.3 Service Layer

#### 4.3.1 `SupplierService` (`src/services/supplier_service.py`)

| Method | Returns | Description |
|---|---|---|
| `get_all_suppliers(active_only=True)` | `list[dict]` | Serialised supplier list with `reliability_score`, `open_po_count`, `default_lead_time_days` |
| `get_supplier(supplier_id)` | `dict \| None` | Full supplier detail including recent performance records |
| `create_supplier(name, lead_time_days, **kwargs)` | `dict` | Validates name uniqueness; creates Supplier row |
| `update_supplier(supplier_id, **fields)` | `dict \| None` | Partial update; re-validates name if changed |
| `deactivate_supplier(supplier_id)` | `bool` | Sets `active=False`; raises `ValueError` if supplier has open POs |
| `compute_reliability_score(supplier_id, window_days=180)` | `float \| None` | `on_time_count / total_count` over window; returns `None` if no records |
| `refresh_lead_time_stats(supplier_id)` | `tuple[float, float]` | Recomputes mean/std from `SupplierPerformanceRecord`; writes back to `Supplier` |
| `get_supplier_performance_summary(supplier_id)` | `dict` | `{on_time_rate, avg_fill_rate, avg_lead_days, std_lead_days, record_count}` |

**Reliability score formula:**

```python
def compute_reliability_score(self, supplier_id: int, window_days: int = 180) -> float | None:
    records = self._repo.get_performance_records(supplier_id, days=window_days)
    if not records:
        return None
    return sum(1 for r in records if r.on_time) / len(records)
    # e.g. 9/10 on-time deliveries → reliability_score = 0.90
```

---

#### 4.3.2 `PurchaseOrderService` (`src/services/purchase_order_service.py`)

| Method | Returns | Description |
|---|---|---|
| `get_all_pos(status=None)` | `list[dict]` | Serialised PO list; joins supplier name, product SKU, product name |
| `get_po(po_id)` | `dict \| None` | Full PO detail including supplier, product, linked alert, performance record |
| `create_po(supplier_id, product_id, ordered_qty, unit_price=None, **kwargs)` | `dict` | Validates supplier and product exist; auto-generates `po_number`; status=DRAFT |
| `create_po_from_alert(alert_id, supplier_id, unit_price=None)` | `dict` | Reads `ReplenishmentAlert` → `InventoryPolicy.suggested_order_qty`; creates draft PO |
| `submit_po(po_id)` | `dict` | DRAFT → SUBMITTED; sets `ordered_at = now()` |
| `confirm_po(po_id, expected_arrival)` | `dict` | SUBMITTED → CONFIRMED; sets `expected_arrival` |
| `receive_po(po_id, actual_qty_received, received_at=None)` | `dict` | CONFIRMED → RECEIVED; computes `lead_time_actual_days`; creates `SupplierPerformanceRecord`; triggers `SupplierService.refresh_lead_time_stats()` |
| `cancel_po(po_id, reason=None)` | `dict` | Any non-terminal status → CANCELLED; records cancellation reason in `notes` |
| `get_open_po_summary()` | `dict` | `{total_open_value, pending_count, confirmed_count, overdue_count}` |

**PO number generation:**

```python
def _generate_po_number(self, session: Session) -> str:
    date_str = datetime.utcnow().strftime("%Y%m%d")
    seq = self._po_repo.get_next_po_sequence(date_str)
    return f"{PO_NUMBER_PREFIX}-{date_str}-{seq:04d}"
    # e.g. "PO-20260220-0001"
```

**`create_po_from_alert()` flow:**

```
1. Load ReplenishmentAlert by alert_id
   ├── Must be STOCKOUT or BELOW_ROP type; raises ValueError otherwise
   └── Must not already have a linked PurchaseOrder (alert.purchase_order_id IS NOT NULL → raise)

2. Load linked InventoryPolicy (via alert.optimization_run_id + alert.product_id)
   └── ordered_qty = policy.suggested_order_qty

3. Create PurchaseOrder(
       supplier_id   = supplier_id,
       product_id    = alert.product_id,
       ordered_qty   = policy.suggested_order_qty,
       alert_id      = alert.id,
       optimization_run_id = alert.optimization_run_id,
       status        = "DRAFT",
   )

4. Update ReplenishmentAlert.purchase_order_id = new_po.id

5. Return serialised PO dict
```

---

### 4.4 Lead-Time-Variance Safety Stock Formula

Phase 5 used the standard safety stock formula:

```
SS = z × σ_d × √L̄
```

where `σ_d` = per-period demand standard deviation and `L̄` = average lead time in periods.

Phase 7 extends this to account for lead-time variability when a supplier's `lead_time_std_days > 0`:

```
SS = z × √(L̄ × σ_d² + D̄² × σ_L²)
```

Where:
- `L̄` = `Supplier.default_lead_time_days` (average lead time, periods)
- `σ_d` = per-period demand standard deviation (from `DemandForecast.demand_std`)
- `D̄` = average daily demand (from `DemandForecast.forecast_mean`)
- `σ_L` = `Supplier.lead_time_std_days` (lead time standard deviation, periods)
- `z` = service-level z-score (from `SAFETY_STOCK_Z_SCORES[service_level]`)

**Formula source:** Silver, Pyke & Peterson — *Inventory Management and Production Planning and Scheduling* (3rd ed., §7.4).

**Implementation in `OptimizationService`:**

```python
def _compute_safety_stock(
    self,
    z: float,
    demand_std: float,
    avg_lead_time: float,
    avg_demand: float,
    lead_time_std: float,
) -> int:
    """
    Extended SS formula when lead_time_std > 0;
    falls back to standard formula when lead_time_std == 0.
    """
    if lead_time_std > 0:
        variance = avg_lead_time * demand_std**2 + avg_demand**2 * lead_time_std**2
        ss = z * math.sqrt(variance)
    else:
        ss = z * demand_std * math.sqrt(avg_lead_time)
    return math.ceil(ss)
```

**Flag in `config/constants.py`:**

```python
SS_USE_LEAD_TIME_VARIANCE = True
# When True: uses z × sqrt(L̄σ_d² + D̄²σ_L²)
# When False: falls back to legacy z × σ_d × sqrt(L̄)  (Phase 5 formula)
```

**Worked example (SKU009, lead time = 21d, σ_L = 3d):**

| Parameter | Value |
|---|---|
| `z` (95% service level) | 1.645 |
| `D̄` (avg daily demand) | 2.52 units/day |
| `σ_d` (demand std, daily) | 0.89 units/day |
| `L̄` (avg lead time) | 21 days |
| `σ_L` (lead time std) | 3 days |
| Variance | 21 × 0.89² + 2.52² × 3² = 16.62 + 57.15 = 73.77 |
| √Variance | 8.59 |
| **SS (extended)** | ceil(1.645 × 8.59) = **15 units** |
| SS (Phase 5 standard) | ceil(1.645 × 0.89 × √21) = **7 units** |

The extended formula correctly accounts for the 3-day delivery uncertainty of SKU009's supplier, increasing the safety buffer from 7 to 15 units.

---

### 4.5 KPI Service Extension (`src/services/kpi_service.py`)

Four new procurement KPIs added to `get_executive_kpis()`:

| KPI Key | Source | Description |
|---|---|---|
| `open_po_count` | `COUNT(purchase_order WHERE status IN (DRAFT, SUBMITTED, CONFIRMED))` | Open purchase orders awaiting delivery |
| `open_po_value` | `SUM(total_value WHERE status IN (SUBMITTED, CONFIRMED))` | $ committed to open orders |
| `supplier_on_time_rate` | `AVG(reliability_score WHERE active=True)` across all active suppliers | Fleet-wide on-time delivery rate (%) |
| `overdue_po_count` | `COUNT(purchase_order WHERE status=CONFIRMED AND expected_arrival < NOW())` | POs past their expected arrival date |

Each KPI returns `*_delta` and `*_direction` computed against the prior week's snapshot (stored in a lightweight `KPISnapshot` table, added in Phase 7).

---

### 4.6 Report Service Extension (`src/services/report_service.py`)

| New Method | Returns | Description |
|---|---|---|
| `get_open_po_summary()` | `dict` | `{total_open_value, pending_count, confirmed_count, overdue_count}` — used in ExecutiveView Procurement section |
| `get_supplier_performance_table()` | `list[dict]` | All active suppliers with `reliability_score`, `avg_lead_days`, `open_po_count`, `total_po_value` — used in PDF Policy Report "Suppliers" sheet and Excel "Suppliers" worksheet |
| `get_po_pipeline(status_filter=None)` | `list[dict]` | Full PO list with supplier name, product SKU, status, value — used in PDF and Excel reports |

---

### 4.7 Presentation Layer

#### 4.7.1 `SuppliersView` (`src/ui/views/suppliers_view.py`)

```
┌────────────────────────────────────────────────────────────┐
│  SUPPLIERS                    [+ Add Supplier]  [Refresh]  │
├────────────────────────────────────────────────────────────┤
│  Search: [_____________]  Active only: [✓]                  │
├──────┬──────────────────┬────────┬─────────────┬──────┬───┤
│  ID  │  Name            │ L/T(d) │ Reliability │  POs │ ✓ │
├──────┼──────────────────┼────────┼─────────────┼──────┼───┤
│   1  │ Alpha Supply Co  │   7    │  ████ 90%   │   3  │ ✓ │
│   2  │ Beta Logistics   │  14    │  ██   50%   │   1  │ ✓ │
│   3  │ Gamma Parts Ltd  │  21    │  ███  71%   │   0  │ ✓ │
│  ... │                  │        │             │      │   │
└──────┴──────────────────┴────────┴─────────────┴──────┴───┘
│  [Edit]  [Deactivate]  [View POs →]                        │
├────────────────────────────────────────────────────────────┤
│  SELECTED SUPPLIER DETAIL (bottom panel)                   │
│  Alpha Supply Co  |  Contact: Jane Smith  |  7d avg lead   │
│  Reliability: 90%  |  Fill Rate: 98%  |  10 deliveries     │
│  Lead Time History: 7d, 6d, 8d, 7d, 9d, 6d (σ = 1.1d)   │
└────────────────────────────────────────────────────────────┘
```

**Add/Edit Supplier modal (`CTkToplevel`):**
- Name (required)
- Contact name / Email / Phone (optional)
- Default lead time days (integer, required, min 1)
- Lead time std days (float, optional, default 0.0 — populated automatically after first delivery)
- Notes

**Reliability mini-bar:** `tkinter.Canvas`-drawn horizontal bar coloured by score:
- ≥ 90%: `#2fa572` (green)
- 70–89%: `#e8a838` (amber)
- < 70%: `#d64545` (red)

---

#### 4.7.2 `PurchaseOrdersView` (`src/ui/views/purchase_orders_view.py`)

```
┌───────────────────────────────────────────────────────────────────────┐
│  PURCHASE ORDERS              Status: [All ▼]     [+ New PO]          │
├────────┬────────────────┬────────────┬────┬────────────┬──────┬──────┤
│ PO #   │ Supplier       │ Product    │ AB │ Status     │  Qty │ $Val │
├────────┼────────────────┼────────────┼────┼────────────┼──────┼──────┤
│PO-0001 │ Alpha Supply   │ Gadget Ult │ A  │ SUBMITTED  │  105 │ $840 │
│PO-0002 │ Beta Logistics │ Gadget Lit │ B  │ CONFIRMED  │   80 │ $480 │
│PO-0003 │ Alpha Supply   │ Power Drl  │ A  │ DRAFT      │   60 │  —   │
│  ...   │                │            │    │            │      │      │
└────────┴────────────────┴────────────┴────┴────────────┴──────┴──────┘
│  [Submit]  [Confirm…]  [Receive…]  [Cancel]  [View Alert →]           │
├───────────────────────────────────────────────────────────────────────┤
│  OPEN PO SUMMARY                                                       │
│  Open Value: $4,820  |  Pending: 3  |  Confirmed: 2  |  Overdue: 0   │
└───────────────────────────────────────────────────────────────────────┘
```

**Status badge colours:**

| Status | Colour |
|---|---|
| DRAFT | `#6b7280` (grey) |
| SUBMITTED | `#1f6aa5` (blue) |
| CONFIRMED | `#e8a838` (amber) |
| RECEIVED | `#2fa572` (green) |
| CANCELLED | `#d64545` (red, strikethrough) |

**Receive PO modal (`CTkToplevel`):**
- PO number and product info (read-only)
- Actual Qty Received (integer, pre-filled with `ordered_qty`)
- Received At (date picker, defaults to today)
- Notes
- Calls `PurchaseOrderService.receive_po()`; triggers `SupplierService.refresh_lead_time_stats()` automatically

---

#### 4.7.3 `AlertsView` Extension

New action button on each qualifying alert row:

| Alert Type | Button |
|---|---|
| STOCKOUT | `[Create PO Draft →]` (primary colour, enabled) |
| BELOW_ROP | `[Create PO Draft →]` (primary colour, enabled) |
| APPROACHING_ROP | `[Create PO Draft →]` (secondary colour, enabled) |
| EXCESS | *(no PO button — overstocked)* |

On click: opens a small modal asking the user to select a supplier (dropdown of active suppliers), confirm the `suggested_order_qty` (editable), then calls `PurchaseOrderService.create_po_from_alert()`. After creation, the alert row shows a "PO #PO-YYYYMMDD-NNNN" badge in place of the button.

---

#### 4.7.4 `OptimizationView` Extension

Two new columns added to the per-product policy table:

| Column | Width | Source |
|---|---|---|
| Supplier | 140 px | `Product.supplier_id` → `Supplier.name`; "(unassigned)" if null |
| L/T Std (d) | 60 px | `Supplier.lead_time_std_days`; "—" if no supplier |

Supplier column is editable: clicking the cell opens a `CTkOptionMenu` of active suppliers. Assignment writes `Product.supplier_id`. Changing the supplier triggers a recalculation preview of the SS using the extended formula.

---

#### 4.7.5 `ExecutiveView` Extension — Procurement Section

New Section E added between the existing Section D (risk table + alert history) and the bottom action bar:

```
├──────────────────────────────────────────────────────────────────────┤
│  PROCUREMENT                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  5 Open  │  │  $4,820  │  │  82.0%   │  │  0 Late  │            │
│  │  Orders  │  │  Open PO │  │ Supplier │  │  Overdue │            │
│  │          │  │   Value  │  │ On-Time  │  │   POs    │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│  [View All Purchase Orders →]                                        │
└──────────────────────────────────────────────────────────────────────┘
```

Four new `KPICard` widgets using the existing `KPICard` component. The "View All Purchase Orders →" link navigates to `PurchaseOrdersView`.

---

#### 4.7.6 App Navigation Extension

Two new sidebar navigation buttons added after the existing Reports button:

- **"Suppliers"** (10th position) — navigates to `SuppliersView`
- **"Purchase Orders"** (11th position) — navigates to `PurchaseOrdersView`

`SuppliersView` and `PurchaseOrdersView` instantiated lazily on first navigation click.

---

## 5. Data Flow

### 5.1 PO Draft Generation from Alert

```
Buyer clicks [Create PO Draft →] on a STOCKOUT alert in AlertsView
    │
    ▼
AlertsView._on_create_po_draft(alert_id)
    │
    ▼
CreatePOModal (CTkToplevel)
    ├── Supplier dropdown (active suppliers)
    ├── Qty field (pre-filled: policy.suggested_order_qty)
    ├── Unit price field (optional)
    └── [Create Draft] button
            │ (on confirm)
            ▼
    PurchaseOrderService.create_po_from_alert(
        alert_id    = alert.id,
        supplier_id = selected_supplier_id,
        unit_price  = entered_price or None,
    )
        ├── Load ReplenishmentAlert (validate type is STOCKOUT/BELOW_ROP)
        ├── Load InventoryPolicy (get suggested_order_qty)
        ├── Generate po_number = PO-20260220-0001
        ├── INSERT PurchaseOrder(status="DRAFT", ordered_qty=policy.suggested_order_qty)
        ├── UPDATE ReplenishmentAlert.purchase_order_id = new_po.id
        └── Return serialised PO dict
                │
                ▼
    AlertsView refreshes — alert row now shows "PO-20260220-0001" badge
    AlertsView shows toast: "Draft PO PO-20260220-0001 created."
```

### 5.2 PO Receipt Confirmation Flow

```
Buyer selects a CONFIRMED PO in PurchaseOrdersView, clicks [Receive…]
    │
    ▼
ReceivePOModal (CTkToplevel)
    ├── Shows: PO number, supplier, product, ordered_qty, expected_arrival
    ├── Actual Qty Received: [105] (editable)
    ├── Received At: [2026-02-27] (date picker)
    └── [Confirm Receipt] button
            │
            ▼
    PurchaseOrderService.receive_po(
        po_id               = po.id,
        actual_qty_received = 105,
        received_at         = date(2026, 2, 27),
    )
        ├── Compute lead_time_actual_days = (received_at - ordered_at).days = 7
        ├── UPDATE PurchaseOrder(status=RECEIVED, received_at=..., actual_days=7)
        ├── INSERT SupplierPerformanceRecord(
        │       supplier_id   = po.supplier_id,
        │       promised_days = supplier.default_lead_time_days,
        │       actual_days   = 7,
        │       on_time       = (7 <= promised_days),
        │       qty_fill_rate = 105 / 105 = 1.0,
        │   )
        ├── SupplierService.refresh_lead_time_stats(supplier_id)
        │       → recomputes mean/std from all SupplierPerformanceRecord rows
        │       → writes back: Supplier.lead_time_std_days = new_std
        └── SupplierService.compute_reliability_score(supplier_id, window_days=180)
                → writes back: Supplier.reliability_score = on_time_fraction
                        │
                        ▼
    PurchaseOrdersView refreshes — PO row now shows RECEIVED (green)
    Inventory update reminder toast: "Receipt recorded. Remember to update stock level."
```

### 5.3 Supplier Reliability Score Computation

```
After each PO receipt:
    1. SupplierPerformanceRecord created (actual_days, on_time, qty_fill_rate)
    2. SupplierService.refresh_lead_time_stats(supplier_id):
          records = last 180 days of SupplierPerformanceRecord
          Supplier.default_lead_time_days = mean(records.actual_days)   [advisory update]
          Supplier.lead_time_std_days     = std(records.actual_days)
    3. SupplierService.compute_reliability_score(supplier_id, window_days=180):
          Supplier.reliability_score = sum(on_time) / count(records)
    4. Next OptimizationService.run_optimization() picks up updated
       lead_time_std_days and uses extended SS formula for this supplier's products
```

---

## 6. PO Status Workflow

```
         ┌──────────┐
         │  DRAFT   │  ← PO created (manually or from alert)
         └──────────┘
               │  submit_po()
               ▼
        ┌────────────┐
        │ SUBMITTED  │  ← ordered_at set; sent to supplier
        └────────────┘
               │  confirm_po(expected_arrival)
               ▼
        ┌────────────┐
        │ CONFIRMED  │  ← supplier confirmed delivery date
        └────────────┘
               │  receive_po(actual_qty, received_at)
               ▼
        ┌──────────┐
        │ RECEIVED │  ← goods received; SupplierPerformanceRecord created
        └──────────┘

Any non-terminal state → cancel_po() → CANCELLED
```

**Terminal states:** RECEIVED, CANCELLED (no further transitions allowed)

**Status validation in `PurchaseOrderService`:**

```python
_VALID_TRANSITIONS = {
    "DRAFT":     {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"RECEIVED",  "CANCELLED"},
    "RECEIVED":  set(),   # terminal
    "CANCELLED": set(),   # terminal
}
```

---

## 7. New Configuration Constants (`config/constants.py`)

| Constant | Default | Description |
|---|---|---|
| `PO_NUMBER_PREFIX` | `"PO"` | PO number prefix; format: `{PO_NUMBER_PREFIX}-YYYYMMDD-NNNN` |
| `PO_STATUS_DRAFT` | `"DRAFT"` | Draft PO (not yet submitted to supplier) |
| `PO_STATUS_SUBMITTED` | `"SUBMITTED"` | Sent to supplier; awaiting confirmation |
| `PO_STATUS_CONFIRMED` | `"CONFIRMED"` | Supplier confirmed delivery date |
| `PO_STATUS_RECEIVED` | `"RECEIVED"` | Goods received; PO closed |
| `PO_STATUS_CANCELLED` | `"CANCELLED"` | PO cancelled; no delivery expected |
| `PO_OPEN_STATUSES` | `("DRAFT", "SUBMITTED", "CONFIRMED")` | Statuses counted as open in KPI queries |
| `SUPPLIER_RELIABILITY_WINDOW_DAYS` | `180` | Rolling window (days) for reliability score and lead-time std computation |
| `SUPPLIER_MIN_RECORDS_FOR_SCORE` | `3` | Minimum `SupplierPerformanceRecord` count required before showing reliability score |
| `SS_USE_LEAD_TIME_VARIANCE` | `True` | When True, uses `z × √(L̄σ_d² + D̄²σ_L²)` extended formula |
| `SS_LEAD_TIME_VARIANCE_MIN_STD` | `0.5` | Minimum `lead_time_std_days` before extended formula activates; below this, standard formula used |
| `PO_OVERDUE_WARNING_DAYS` | `0` | Days past `expected_arrival` before a CONFIRMED PO is flagged overdue |
| `EXECUTIVE_PROCUREMENT_KPIS` | `("open_po_count", "open_po_value", "supplier_on_time_rate", "overdue_po_count")` | KPI keys shown in Procurement section |

---

## 8. Technology Stack (Phase 7 Additions)

No new third-party packages required. All Phase 7 functionality is implemented using packages already present from Phases 1–6:

| Capability | Package (already installed) | Usage |
|---|---|---|
| ORM + DB | SQLAlchemy + SQLite | Supplier, PurchaseOrder, SupplierPerformanceRecord models |
| Statistics | Python `statistics` module (stdlib) | `mean()` and `stdev()` for lead-time statistics |
| Date arithmetic | Python `datetime` (stdlib) | Lead time computation (`received_at - ordered_at`).days |
| UI | CustomTkinter | SuppliersView, PurchaseOrdersView, modals |
| PDF/Excel | reportlab + openpyxl (Phase 6) | POLICY report "Suppliers" section |
| Math | Python `math` (stdlib) | `math.sqrt()`, `math.ceil()` in extended SS formula |

**Updated `requirements.txt`:** No new entries (Phase 7 relies entirely on Phase 1–6 dependencies).

---

## 9. Implementation Tasks

### 9.1 Constants & ORM (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T7-01 | Add Phase 7 constants to `config/constants.py` | `config/constants.py` | 15 min |
| T7-02 | Add `Supplier`, `PurchaseOrder`, `SupplierPerformanceRecord` ORM models + relationships | `src/database/models.py` | 45 min |
| T7-03 | Database migration for 3 new tables | Bash / SQLAlchemy `create_all()` | 10 min |

### 9.2 Repository Layer (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T7-04 | Implement `SupplierRepository` (8 methods) | `src/repositories/supplier_repository.py` | 1.5 h |
| T7-05 | Implement `PurchaseOrderRepository` (9 methods) | `src/repositories/purchase_order_repository.py` | 2 h |

### 9.3 Service Layer (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T7-06 | Implement `SupplierService` (8 methods + reliability scoring) | `src/services/supplier_service.py` | 3 h |
| T7-07 | Implement `PurchaseOrderService` (9 methods + PO number generation + status transitions) | `src/services/purchase_order_service.py` | 4 h |
| T7-08 | Extend `OptimizationService` with lead-time-variance SS formula | `src/services/optimization_service.py` | 2 h |
| T7-09 | Extend `KPIService` with 4 procurement KPIs | `src/services/kpi_service.py` | 1 h |
| T7-10 | Extend `ReportService` with PO summary and supplier performance methods | `src/services/report_service.py` | 1.5 h |

### 9.4 UI Layer (Priority: Medium)

| # | Task | Module | Effort |
|---|---|---|---|
| T7-11 | Implement `SuppliersView` (list + add/edit modal + detail panel) | `src/ui/views/suppliers_view.py` | 5 h |
| T7-12 | Implement `PurchaseOrdersView` (pipeline table + receive modal + summary strip) | `src/ui/views/purchase_orders_view.py` | 6 h |
| T7-13 | Extend `AlertsView` with "Create PO Draft" button and CreatePOModal | `src/ui/views/alerts_view.py` | 2.5 h |
| T7-14 | Extend `OptimizationView` with supplier selector and lead-time std column | `src/ui/views/optimization_view.py` | 2 h |
| T7-15 | Extend `ExecutiveView` with Procurement KPIs section (Section E) | `src/ui/views/executive_view.py` | 1.5 h |
| T7-16 | Register Suppliers + Purchase Orders views in `App` navigation | `src/ui/app.py` | 20 min |

### 9.5 Testing (Priority: High)

| # | Task | Module | Effort |
|---|---|---|---|
| T7-17 | Write `tests/test_supplier_repository.py` (7 tests) | `tests/test_supplier_repository.py` | 1.5 h |
| T7-18 | Write `tests/test_po_repository.py` (8 tests) | `tests/test_po_repository.py` | 2 h |
| T7-19 | Write `tests/test_supplier_service.py` (8 tests) | `tests/test_supplier_service.py` | 2 h |
| T7-20 | Write `tests/test_purchase_order_service.py` (9 tests) | `tests/test_purchase_order_service.py` | 2.5 h |
| T7-21 | Write `tests/test_supplier_reliability.py` (7 tests) | `tests/test_supplier_reliability.py` | 1.5 h |
| T7-22 | Write `tests/test_po_generation.py` (6 tests) | `tests/test_po_generation.py` | 1.5 h |
| T7-23 | Write `tests/test_extended_ss_formula.py` (6 tests) | `tests/test_extended_ss_formula.py` | 1.5 h |

**Total estimated effort: 40–55 hours**

---

## 10. Implementation Order

```
Step 1: Constants & ORM
  ├── T7-01: Constants
  ├── T7-02: ORM models (Supplier, PurchaseOrder, SupplierPerformanceRecord)
  └── T7-03: Database migration

Step 2: Repository Layer
  ├── T7-04: SupplierRepository
  └── T7-05: PurchaseOrderRepository

Step 3: Service Layer (bottom-up)
  ├── T7-06: SupplierService (depends on T7-04)
  ├── T7-07: PurchaseOrderService (depends on T7-05 + T7-06)
  ├── T7-08: OptimizationService extension (independent of T7-06/07)
  ├── T7-09: KPIService extension (depends on T7-07)
  └── T7-10: ReportService extension (depends on T7-06 + T7-07)

Step 4: Testing (immediately after each component)
  ├── T7-17: SupplierRepository tests    ← after T7-04
  ├── T7-18: PurchaseOrderRepository tests ← after T7-05
  ├── T7-19: SupplierService tests        ← after T7-06
  ├── T7-20: PurchaseOrderService tests   ← after T7-07
  ├── T7-21: Reliability scoring tests    ← after T7-06
  ├── T7-22: PO generation tests          ← after T7-07
  └── T7-23: Extended SS formula tests    ← after T7-08

Step 5: UI Layer (build after service layer is fully tested)
  ├── T7-11: SuppliersView
  ├── T7-12: PurchaseOrdersView
  ├── T7-13: AlertsView extension (Create PO Draft)
  ├── T7-14: OptimizationView extension (supplier selector)
  ├── T7-15: ExecutiveView Procurement section
  └── T7-16: App navigation (Suppliers + POs buttons)
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| `create_po_from_alert()` called on alert with no linked `InventoryPolicy` (product added after optimization run) | High | Low | Guard: if no `InventoryPolicy` found for alert's `(optimization_run_id, product_id)`, fall back to asking user to enter `ordered_qty` manually |
| Circular FK between `PurchaseOrder.alert_id` → `ReplenishmentAlert` and potential `ReplenishmentAlert.purchase_order_id` back-reference | Medium | Medium | Use nullable FKs in both directions; avoid SQLAlchemy `cascade="all, delete-orphan"` on this circular pair |
| `statistics.stdev()` raises `StatisticsError` if only 1 performance record | Low | High | Guard with `if len(records) < 2: return 0.0`; stdev requires at least 2 data points |
| Extended SS formula produces lower SS than standard formula in edge cases (`σ_L → 0`) | Low | Medium | Added `SS_LEAD_TIME_VARIANCE_MIN_STD = 0.5` constant; below this threshold falls back to standard formula |
| Buyer submits/confirms/receives PO in wrong order (state machine violation) | High | Low | `_VALID_TRANSITIONS` dict enforced in `PurchaseOrderService`; raises `InvalidTransitionError` with descriptive message |
| PO number sequence collision on concurrent use (same date, two users) | Low | Low | `get_next_po_sequence()` uses `SELECT MAX(seq) FOR UPDATE` equivalent; SQLite serialises writes anyway |
| `SuppliersView` add/edit modal attempts to save duplicate supplier name | Low | Medium | `SupplierRepository.create()` catches `IntegrityError`; service layer maps to user-visible `"Supplier name already exists"` error message |
| `OptimizationView` supplier selector re-runs SS preview on every selection change (performance concern for 20 products) | Medium | Medium | SS preview runs only on explicit user action (button click), not on every dropdown change |
| Lead time std growing over time as outlier deliveries accumulate | Medium | Low | `SUPPLIER_RELIABILITY_WINDOW_DAYS = 180` caps the rolling window; outliers older than 180 days are excluded |

---

## 12. Testing Strategy

### 12.1 Supplier Repository Tests (`tests/test_supplier_repository.py`)

| Test | Validates |
|---|---|
| `test_create_supplier_basic` | `create()` inserts row; `get_by_id()` returns it with correct `name` and `default_lead_time_days` |
| `test_create_supplier_duplicate_name_raises` | Second `create()` with same name raises `IntegrityError` |
| `test_get_all_active_only` | `get_all(active_only=True)` excludes deactivated suppliers |
| `test_deactivate_supplier` | `deactivate()` sets `active=False`; `get_by_id()` still returns the row |
| `test_update_supplier_fields` | `update(supplier_id, email="new@email.com")` changes only the specified field |
| `test_get_performance_records_window` | Records older than `SUPPLIER_RELIABILITY_WINDOW_DAYS` are excluded |
| `test_get_lead_time_statistics_no_records` | Returns `(default_lead_time_days, 0.0)` when no `SupplierPerformanceRecord` rows exist |

### 12.2 Purchase Order Repository Tests (`tests/test_po_repository.py`)

| Test | Validates |
|---|---|
| `test_create_po_auto_number` | `create()` generates `po_number` matching `PO-YYYYMMDD-NNNN` format |
| `test_po_number_sequence_increments` | Second PO on same date gets sequence `0002` |
| `test_get_all_status_filter` | `get_all(status="SUBMITTED")` returns only SUBMITTED POs |
| `test_get_open_for_product` | Returns DRAFT+SUBMITTED+CONFIRMED POs for a product; excludes RECEIVED/CANCELLED |
| `test_update_status_submitted` | `update_status(po_id, "SUBMITTED")` sets `ordered_at` to a non-null datetime |
| `test_update_status_received` | `update_status(po_id, "RECEIVED", actual_qty_received=100)` sets `received_at` and `actual_qty_received` |
| `test_get_total_open_value` | SUM of `total_value` for SUBMITTED+CONFIRMED POs; excludes DRAFT (no price) and RECEIVED |
| `test_get_by_po_number` | Returns correct PO; returns `None` for non-existent number |

### 12.3 Supplier Service Tests (`tests/test_supplier_service.py`)

| Test | Validates |
|---|---|
| `test_create_and_retrieve_supplier` | Round-trip: create → get returns dict with correct fields |
| `test_deactivate_with_open_po_raises` | `deactivate_supplier()` raises `ValueError` when open POs exist |
| `test_deactivate_without_open_po_succeeds` | Supplier with only RECEIVED/CANCELLED POs can be deactivated |
| `test_compute_reliability_score_perfect` | 5/5 on-time records → `reliability_score == 1.0` |
| `test_compute_reliability_score_partial` | 3/5 on-time → `reliability_score == 0.6` |
| `test_compute_reliability_score_insufficient_records` | Fewer than `SUPPLIER_MIN_RECORDS_FOR_SCORE` records → returns `None` |
| `test_refresh_lead_time_stats_updates_supplier` | After `refresh_lead_time_stats()`: `Supplier.lead_time_std_days` matches `stdev([actual_days])` |
| `test_get_performance_summary` | `{on_time_rate, avg_fill_rate, avg_lead_days, std_lead_days, record_count}` all present and correct |

### 12.4 Purchase Order Service Tests (`tests/test_purchase_order_service.py`)

| Test | Validates |
|---|---|
| `test_create_po_sets_draft_status` | New PO has `status == "DRAFT"` |
| `test_submit_po_sets_ordered_at` | After `submit_po()`: `status == "SUBMITTED"` and `ordered_at` is not None |
| `test_confirm_po_sets_expected_arrival` | After `confirm_po(expected_arrival=date)`: `status == "CONFIRMED"` and `expected_arrival == date` |
| `test_receive_po_creates_performance_record` | After `receive_po()`: `SupplierPerformanceRecord` row created with correct `actual_days` and `on_time` flag |
| `test_receive_po_updates_supplier_stats` | After `receive_po()`: `Supplier.reliability_score` and `lead_time_std_days` updated |
| `test_cancel_po_from_draft` | `cancel_po()` on DRAFT PO → `status == "CANCELLED"` |
| `test_invalid_transition_raises` | `confirm_po()` on DRAFT (skipping SUBMITTED) → raises `InvalidTransitionError` |
| `test_receive_terminal_state_raises` | `submit_po()` on RECEIVED PO → raises `InvalidTransitionError` |
| `test_create_po_from_alert_sets_qty` | PO `ordered_qty` equals `InventoryPolicy.suggested_order_qty` for the alert's product |

### 12.5 Supplier Reliability Tests (`tests/test_supplier_reliability.py`)

| Test | Validates |
|---|---|
| `test_reliability_score_zero_on_time` | 0/4 on-time → `reliability_score == 0.0` |
| `test_reliability_window_excludes_old_records` | Record at 200 days ago excluded from 180-day window |
| `test_stdev_single_record_returns_zero` | `refresh_lead_time_stats()` with 1 record → `lead_time_std_days == 0.0` (no crash) |
| `test_fill_rate_partial_shipment` | 80 units received out of 100 ordered → `qty_fill_rate == 0.8` |
| `test_on_time_flag_exact_match` | `actual_days == promised_days` → `on_time == True` |
| `test_on_time_flag_early` | `actual_days < promised_days` → `on_time == True` |
| `test_on_time_flag_late` | `actual_days > promised_days` → `on_time == False` |

### 12.6 PO Generation Tests (`tests/test_po_generation.py`)

| Test | Validates |
|---|---|
| `test_create_po_from_stockout_alert` | STOCKOUT alert → PO created with `alert_id` linked |
| `test_create_po_from_below_rop_alert` | BELOW_ROP alert → PO created successfully |
| `test_create_po_from_excess_alert_raises` | EXCESS alert → `ValueError` (no PO for excess alerts) |
| `test_create_po_from_alert_already_linked_raises` | Alert already has a `purchase_order_id` → `ValueError` |
| `test_po_links_alert_back_reference` | After PO creation: `ReplenishmentAlert.purchase_order_id == new_po.id` |
| `test_po_qty_matches_suggested_order_qty` | `PurchaseOrder.ordered_qty == InventoryPolicy.suggested_order_qty` |

### 12.7 Extended SS Formula Tests (`tests/test_extended_ss_formula.py`)

| Test | Validates |
|---|---|
| `test_extended_ss_formula_sku009_worked_example` | SS for SKU009 with σ_L=3d = 15 units (matches §4.4 worked example) |
| `test_standard_formula_when_std_zero` | `lead_time_std_days == 0` → uses standard formula; SS matches Phase 5 value |
| `test_extended_formula_exceeds_standard` | For any `lead_time_std_days > SS_LEAD_TIME_VARIANCE_MIN_STD`, extended SS ≥ standard SS |
| `test_flag_disabled_uses_standard_formula` | `SS_USE_LEAD_TIME_VARIANCE = False` → standard formula regardless of `lead_time_std_days` |
| `test_min_std_threshold` | `lead_time_std_days = 0.3` (below `SS_LEAD_TIME_VARIANCE_MIN_STD = 0.5`) → standard formula |
| `test_ss_always_integer` | Extended formula result always `int` (via `math.ceil()`); never float |

---

## 13. Non-Functional Requirements (Phase 7)

| Requirement | Target | Validation Method |
|---|---|---|
| `create_po_from_alert()` response time | < 0.5 s | Timed in `test_create_po_from_stockout_alert` |
| `receive_po()` including stats refresh | < 1 s | Timed; ≤ 10 performance records expected in early use |
| `SuppliersView` initial load (20 suppliers) | < 1 s | Background thread; skeleton shown while loading |
| `PurchaseOrdersView` initial load (100 POs) | < 2 s | Background thread; paginated `DataTable` |
| Extended SS formula computation (20 products) | < 0.1 s | No I/O; pure arithmetic |
| PO number uniqueness under concurrent writes | 100% | SQLite serialised writes; sequence query uses atomic pattern |
| Status transition validation | No invalid transition reaches DB | `_VALID_TRANSITIONS` dict checked before any DB write |
| Non-GUI test coverage | ≥ 90% | `pytest --cov=src --ignore=src/ui` |

---

## 14. Phase 7 Exit Criteria

- [ ] `supplier`, `purchase_order`, `supplier_performance_record` tables created; migration verified via `test_database.py` extension
- [ ] `SupplierService.create_supplier()` creates and retrieves supplier with correct fields
- [ ] `SupplierService.deactivate_supplier()` raises `ValueError` when open POs exist (test: `test_deactivate_with_open_po_raises`)
- [ ] `SupplierService.compute_reliability_score()` returns correct fraction (test: `test_compute_reliability_score_partial`)
- [ ] `PurchaseOrderService` enforces status transitions; invalid transitions raise `InvalidTransitionError`
- [ ] `PurchaseOrderService.receive_po()` creates `SupplierPerformanceRecord` and updates `Supplier.reliability_score` and `lead_time_std_days`
- [ ] `PurchaseOrderService.create_po_from_alert()` correctly links `PurchaseOrder` ↔ `ReplenishmentAlert`; raises `ValueError` for EXCESS alerts
- [ ] Extended SS formula returns 15 units for SKU009 worked example (σ_L=3d, σ_d=0.89, D̄=2.52, z=1.645, L̄=21)
- [ ] Standard formula used when `lead_time_std_days < SS_LEAD_TIME_VARIANCE_MIN_STD` (0.5); results match Phase 5 values
- [ ] `KPIService.get_executive_kpis()` now includes all 4 procurement KPIs (`open_po_count`, `open_po_value`, `supplier_on_time_rate`, `overdue_po_count`)
- [ ] `SuppliersView` renders without exception; Add Supplier modal creates row and refreshes list
- [ ] `PurchaseOrdersView` renders without exception; pipeline table shows correct status badges
- [ ] "Create PO Draft →" button visible on STOCKOUT/BELOW_ROP alerts in `AlertsView`; creates draft PO and shows PO number badge
- [ ] `ExecutiveView` Procurement section (Section E) renders 4 KPI cards; "View All Purchase Orders →" link navigates correctly
- [ ] All 51 new Phase 7 tests pass; total test count = 314; 0 regressions in Phase 1–6 tests
- [ ] Non-GUI test coverage ≥ 90%

---

## 15. Transition to Phase 8

Phase 8 is the final phase of the Logistics DSS. It will consolidate and productionise the system with the following deliverables:

1. **Data Import / Export Wizard:**
   - CSV and Excel import for initial product master data, historical demand, and supplier master
   - Full-database export for backup and migration
   - Phase 8 reuses Phase 6's `ExcelExporter` infrastructure for the export path

2. **User Authentication and Role-Based Access:**
   - `User` ORM model: `username`, `hashed_password`, `role (ADMIN | BUYER | VIEWER)`
   - Login screen replacing the current direct-launch startup
   - `VIEWER` role: read-only access; no PO creation or policy runs
   - `BUYER` role: full access to PO workflow; no system configuration
   - `ADMIN` role: full access including supplier management and database reset

3. **Scheduled Report Generation:**
   - `ReportSchedule` ORM model: `report_type`, `export_format`, `cron_expression`, `output_dir`, `active`
   - Background `APScheduler` (or `threading.Timer`) triggers using Phase 6's `ReportRunner` (no UI dependency)
   - Scheduler status visible in a new Settings view

4. **System Settings and Audit Trail:**
   - Settings view: database path, log level, report export directory, theme (light/dark)
   - `AuditEvent` ORM model: captures login/logout, PO state changes, policy runs, report generation
   - Phase 7's `SupplierPerformanceRecord` and `ReportLog` (Phase 6) integrate into the unified audit trail

5. **Packaging and Deployment:**
   - `pyinstaller` spec for single-file executable (Windows `.exe`, macOS `.app`)
   - `setup.cfg` / `pyproject.toml` for pip-installable distribution
   - Automated test run as part of the build pipeline

**Prerequisites from Phase 7 used by Phase 8:**
- `PurchaseOrderService` and `SupplierService` remain unchanged; Phase 8 adds `created_by` (User FK) to `PurchaseOrder`
- `ReportRunner` remains a pure library call; Phase 8 connects it to `ReportSchedule` triggers
- `KPIService` procurement KPIs feed into Phase 8's system health dashboard
- Phase 7's `_VALID_TRANSITIONS` state machine pattern is adopted for the Phase 8 `AuditEvent` lifecycle

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-02-20 | Initial Phase 7 implementation plan |

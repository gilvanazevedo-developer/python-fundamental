# Logistics DSS - Phase 5 Implementation Plan
# Inventory Optimization

**Project:** Logistics Decision Support System
**Phase:** 5 of 8 - Inventory Optimization
**Author:** Gilvan de Azevedo
**Date:** 2026-02-20
**Status:** Not Started
**Depends on:** Phase 4 (Demand Forecasting) -- functionally complete

---

## 1. Phase 5 Objective

Build an inventory optimization engine that converts Phase 4 demand forecasts into prescriptive inventory policies for every product: Economic Order Quantity (EOQ), Safety Stock (SS), Reorder Point (ROP), and Maximum Stock Level. The engine monitors current stock against computed ROPs, generates prioritized replenishment alerts, and surfaces them in a dedicated Alerts screen and on the Dashboard. This phase transforms the system from descriptive (what is happening) into prescriptive (what to do next), delivering actionable purchasing recommendations.

**Deliverables:**
- Optimization engine with four calculators (EOQ, Safety Stock, ROP, Max Stock) driven by ABC-class service-level targets and forecast RMSE
- Policy Engine orchestrating full portfolio optimization; results persisted per run
- Alert Generator detecting stock-below-ROP conditions, computing suggested order quantities and days-until-stockout
- Optimization View (new screen: policy table, cost breakdown chart, parameter controls)
- Alerts View (new screen: active replenishment alerts sorted by severity, with acknowledgement)
- Dashboard integration: alert KPI cards, critical alerts strip
- Forecast View integration: ROP and EOQ displayed in the demand adequacy table
- Full test suite covering all calculators, the policy engine, and alert logic

---

## 2. Phase 4 Dependencies (Available)

Phase 5 builds directly on the following Phase 4 components:

| Component | Module | Usage in Phase 5 |
|-----------|--------|-------------------|
| DemandForecast model | `src/database/models.py` | `predicted_qty` for annual demand; `rmse` as demand std for safety stock |
| ForecastRun model | `src/database/models.py` | FK linking inventory policies to the forecast run they consumed |
| ForecastRunner | `src/forecasting/forecast_runner.py` | Phase 5 requires a completed forecast run before optimization |
| ForecastService | `src/services/forecast_service.py` | `get_latest_forecast()` per product; `get_accuracy_table()` for RMSE |
| ProductClassification model | `src/database/models.py` | ABC class → service level target; XYZ class → safety stock multiplier |
| AnalyticsService | `src/services/analytics_service.py` | Revenue shares for priority ordering |
| InventoryService | `src/services/inventory_service.py` | `get_stock_by_product()` current stock levels for alert generation |
| SalesService | `src/services/sales_service.py` | Average daily demand cross-check against forecast |
| ForecastView | `src/ui/views/forecast_view.py` | Adequacy table extended with ROP and EOQ columns |
| ChartPanel | `src/ui/components/chart_panel.py` | Extended with cost breakdown stacked bar chart |
| DataTable | `src/ui/components/data_table.py` | Policy and alert tables |
| FilterBar | `src/ui/components/filter_bar.py` | Extended with service level and lead time filters |
| ClassificationBadge | `src/ui/components/classification_badge.py` | Badge display in policy and alert tables |
| DatabaseManager | `src/database/connection.py` | Sessions for policy and alert persistence |
| LoggerMixin | `src/logger.py` | Logging across all new optimization modules |
| Constants | `config/constants.py` | Extended with service levels, holding/ordering costs, and alert thresholds |

---

## 3. Architecture Overview

### 3.1 Phase 5 Directory Structure

```
logistics-dss/
├── config/
│   ├── settings.py             # (existing)
│   └── constants.py            # + service levels, holding cost, lead time, alert thresholds
├── src/
│   ├── optimization/           # NEW: Optimization Engine
│   │   ├── __init__.py
│   │   ├── eoq_calculator.py       # Economic Order Quantity (Wilson formula)
│   │   ├── safety_stock_calculator.py  # Safety stock via RMSE + service level z-score
│   │   ├── rop_calculator.py       # Reorder Point = demand during lead time + SS
│   │   ├── policy_engine.py        # Orchestrator: compute + persist full inventory policy
│   │   └── alert_generator.py      # Detect stock-below-ROP; compute suggested order qty
│   ├── services/
│   │   ├── optimization_service.py # NEW: query layer for policies and alerts
│   │   ├── kpi_service.py          # (existing) + optimization KPIs
│   │   ├── inventory_service.py    # (existing)
│   │   ├── sales_service.py        # (existing)
│   │   ├── analytics_service.py    # (existing)
│   │   └── forecast_service.py     # (existing)
│   ├── database/
│   │   ├── connection.py           # (existing)
│   │   └── models.py               # + OptimizationRun + InventoryPolicy + ReplenishmentAlert
│   └── ui/
│       ├── app.py                  # + Optimization + Alerts nav entries
│       ├── theme.py                # + alert severity color constants
│       ├── components/
│       │   ├── chart_panel.py      # + plot_cost_breakdown() stacked bar
│       │   └── filter_bar.py       # + service level + lead time selectors
│       └── views/
│           ├── forecast_view.py    # (existing) + ROP/EOQ columns in adequacy table
│           ├── dashboard_view.py   # (existing) + alert KPI cards + critical alerts strip
│           ├── optimization_view.py # NEW: Policy management screen
│           └── alerts_view.py      # NEW: Active replenishment alerts screen
├── tests/
│   ├── test_eoq_calculator.py          # NEW: EOQ formula + edge case tests
│   ├── test_safety_stock_calculator.py # NEW: SS via z-score × RMSE × sqrt(L) tests
│   ├── test_rop_calculator.py          # NEW: ROP = demand × lead_time + SS tests
│   ├── test_policy_engine.py           # NEW: Full policy computation + persistence tests
│   ├── test_alert_generator.py         # NEW: Alert detection + prioritization tests
│   └── test_optimization_service.py    # NEW: Service layer integration tests
└── main.py                     # (existing)
```

### 3.2 Layer Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          Presentation Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │Dashboard │  │Inventory │  │Analytics │  │ Forecast │  │Optimization  │ │
│  │ View (+) │  │  View    │  │ View     │  │View (+)  │  │View (NEW)    │ │
│  └────┬─────┘  └──────────┘  └──────────┘  └────┬─────┘  └──────┬───────┘ │
│       │                                          │               │         │
│  ┌────┴──────────────────────────────────────────┴───────────────┴───────┐ │
│  │        Reusable Components (+ extensions)                             │ │
│  │  KPI Card | DataTable | ChartPanel(+) | Badge | AlertBadge (new)      │ │
│  └──────────────────────────┬────────────────────────────────────────────┘ │
│                ┌────────────┴──────────────┐                               │
│                │     Alerts View (NEW)     │                               │
│                └───────────────────────────┘                               │
├────────────────────────────────────────────────────────────────────────── ┤
│                           Service Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Inventory   │  │   Forecast   │  │  Analytics   │  │ Optimization  │  │
│  │  Service     │  │   Service    │  │  Service     │  │ Service (NEW) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────┬───────┘  │
├────────────────────────────────────────────────────────────────┼──────────┤
│                    Optimization Engine (NEW)                               │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                        PolicyEngine                                │   │
│  │   ┌──────────────────────────────────────────────────────────┐    │   │
│  │   │                   Calculators                            │    │   │
│  │   │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │    │   │
│  │   │  │ EOQ         │  │ Safety Stock │  │    ROP        │   │    │   │
│  │   │  │ Calculator  │  │ Calculator   │  │  Calculator   │   │    │   │
│  │   │  └─────────────┘  └──────────────┘  └───────────────┘   │    │   │
│  │   └──────────────────────────────────────────────────────────┘    │   │
│  │                      AlertGenerator                                │   │
│  └────────────────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────────────── ┤
│          Forecasting Engine (Phase 4) + Analytics Engine (Phase 3)        │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  ┌──────────┐ │
│  │  DemandForecast  │  │  ORM Models                      │  │  Sales   │ │
│  │  (predicted_qty, │  │  (+ OptimizationRun,             │  │  Records │ │
│  │   rmse, model)   │  │     InventoryPolicy,             │  │          │ │
│  │                  │  │     ReplenishmentAlert)          │  │          │ │
│  └──────────────────┘  └──────────────────────────────────┘  └──────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Database Model Extension

#### 4.1.1 Supplier Model Extension (`src/database/models.py`)

If `lead_time_days` and `ordering_cost_per_order` are not already columns on the existing `Supplier` model, they are added now:

```python
# Added to existing Supplier model:
lead_time_days         = Column(Integer,  nullable=False, default=7)
ordering_cost_per_order = Column(Float,   nullable=True)   # $ per purchase order
```

- `lead_time_days`: calendar days from order placement to receipt; default 7
- `ordering_cost_per_order`: purchase department cost to process one order; falls back to `DEFAULT_ORDERING_COST` constant if `None`

#### 4.1.2 OptimizationRun (`src/database/models.py`)

Audit header for each portfolio optimization execution:

```python
class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id                   = Column(Integer, primary_key=True)
    run_timestamp        = Column(DateTime, default=func.now())
    forecast_run_id      = Column(Integer, ForeignKey("forecast_runs.id"), nullable=True)
    lookback_forecast_id = Column(Integer, nullable=True)  # snapshot of which ForecastRun used
    total_products       = Column(Integer, nullable=False)
    policies_generated   = Column(Integer, nullable=False)
    alerts_generated     = Column(Integer, nullable=False)
    total_annual_cost    = Column(Float,   nullable=True)   # sum across all products
    run_duration_seconds = Column(Float,   nullable=False)

    policies = relationship("InventoryPolicy",    back_populates="run")
    alerts   = relationship("ReplenishmentAlert", back_populates="run")
```

#### 4.1.3 InventoryPolicy (`src/database/models.py`)

One row per product per optimization run, storing the full computed inventory policy:

```python
class InventoryPolicy(Base):
    __tablename__ = "inventory_policies"

    id                    = Column(Integer, primary_key=True)
    run_id                = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)
    product_id            = Column(Integer, ForeignKey("products.id"),          nullable=False)
    generated_at          = Column(DateTime, default=func.now())

    # Inputs (captured at policy generation time)
    abc_class             = Column(String(1),  nullable=False)
    lead_time_days        = Column(Integer,    nullable=False)
    annual_demand         = Column(Float,      nullable=False)  # units/year from forecast
    daily_demand_mean     = Column(Float,      nullable=False)  # units/day
    demand_rmse           = Column(Float,      nullable=True)   # from DemandForecast.rmse
    ordering_cost         = Column(Float,      nullable=False)  # $ per order
    holding_cost_per_unit = Column(Float,      nullable=False)  # $ per unit per year
    unit_cost             = Column(Float,      nullable=True)   # from Product.cost_price

    # Computed outputs
    service_level_target  = Column(Float,      nullable=False)  # 0.90 / 0.95 / 0.99
    z_score               = Column(Float,      nullable=False)  # norm.ppf(service_level)
    safety_stock          = Column(Float,      nullable=False)  # units
    reorder_point         = Column(Float,      nullable=False)  # units
    eoq                   = Column(Float,      nullable=False)  # units per order
    max_stock_level       = Column(Float,      nullable=False)  # reorder_point + eoq
    avg_inventory         = Column(Float,      nullable=False)  # safety_stock + eoq/2

    # Cost analysis
    annual_ordering_cost  = Column(Float,      nullable=False)  # (D/EOQ) × ordering_cost
    annual_holding_cost   = Column(Float,      nullable=False)  # avg_inv × holding_cost
    annual_purchase_cost  = Column(Float,      nullable=True)   # D × unit_cost
    total_annual_cost     = Column(Float,      nullable=True)   # ordering + holding + purchase
    policy_notes          = Column(Text,       nullable=True)   # warnings, fallback flags

    run     = relationship("OptimizationRun", back_populates="policies")
    product = relationship("Product",         back_populates="policies")
```

**Indexes:**
- `(product_id, generated_at DESC)` — latest policy per product
- `(run_id, product_id)` — per-run retrieval
- `(abc_class, reorder_point)` — alert generation filter

#### 4.1.4 ReplenishmentAlert (`src/database/models.py`)

Generated when current stock falls at or below the computed reorder point:

```python
class ReplenishmentAlert(Base):
    __tablename__ = "replenishment_alerts"

    id                  = Column(Integer,  primary_key=True)
    run_id              = Column(Integer,  ForeignKey("optimization_runs.id"), nullable=False)
    product_id          = Column(Integer,  ForeignKey("products.id"),          nullable=False)
    policy_id           = Column(Integer,  ForeignKey("inventory_policies.id"), nullable=False)

    alert_type          = Column(String(20), nullable=False)
    # Values: "STOCKOUT" | "BELOW_ROP" | "APPROACHING_ROP" | "EXCESS"

    severity            = Column(String(10), nullable=False)
    # Values: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"

    current_stock       = Column(Float,  nullable=False)
    reorder_point       = Column(Float,  nullable=False)
    eoq                 = Column(Float,  nullable=False)
    suggested_order_qty = Column(Float,  nullable=False)    # max(EOQ, ROP - current_stock)
    days_until_stockout = Column(Float,  nullable=True)     # current_stock / daily_demand_mean
    created_at          = Column(DateTime, default=func.now())

    is_acknowledged     = Column(Boolean,   default=False)
    acknowledged_at     = Column(DateTime,  nullable=True)
    acknowledged_by     = Column(String(100), nullable=True)  # user note / reason
    notes               = Column(Text,      nullable=True)

    run     = relationship("OptimizationRun", back_populates="alerts")
    product = relationship("Product")
    policy  = relationship("InventoryPolicy")
```

**Indexes:**
- `(product_id, is_acknowledged, created_at DESC)` — active alerts per product
- `(severity, is_acknowledged)` — severity-filtered alert dashboard
- `(run_id)` — per-run alert retrieval

---

### 4.2 Optimization Engine

#### 4.2.1 EOQ Calculator (`src/optimization/eoq_calculator.py`)

Implements the Wilson (Harris) Economic Order Quantity formula, which minimizes the sum of annual ordering cost and annual holding cost.

**Formula:**
```
EOQ = sqrt(2 × D × S / H)

where:
  D = annual demand (units/year)  ← annualized from 30-day forecast
  S = ordering cost per order ($)  ← from Supplier.ordering_cost_per_order
  H = holding cost per unit per year ($)
      = unit_cost × HOLDING_COST_RATE  (e.g. $50 unit × 0.25/yr = $12.50/yr)
```

**Edge cases:**
- `D <= 0`: no demand → EOQ = 0; policy_notes flagged as "zero demand"
- `H <= 0`: invalid holding cost → raises `InvalidParameterError`
- `S <= 0`: invalid ordering cost → raises `InvalidParameterError`
- Very small EOQ (< 1 unit): rounded up to 1

**Cost verification (EOQ property):**
At EOQ, annual ordering cost = annual holding cost:
```
Annual ordering cost = (D / EOQ) × S
Annual holding cost  = (EOQ / 2 + SS) × H
At EOQ (SS=0): ordering cost = holding cost = sqrt(D × S × H / 2)
```

**Class `EOQCalculator`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `compute(annual_demand, ordering_cost, holding_cost_per_unit) -> float` | EOQ (units) | Wilson formula; raises on invalid params |
| `compute_annual_ordering_cost(annual_demand, eoq, ordering_cost) -> float` | $ | `(D/EOQ) × S` |
| `compute_annual_holding_cost(eoq, safety_stock, holding_cost_per_unit) -> float` | $ | `(EOQ/2 + SS) × H` |
| `compute_total_annual_cost(annual_demand, eoq, safety_stock, ordering_cost, holding_cost, unit_cost) -> float` | $ | `ordering + holding + purchase` |

---

#### 4.2.2 Safety Stock Calculator (`src/optimization/safety_stock_calculator.py`)

Computes the statistical safety stock buffer required to achieve a target service level given demand uncertainty measured by the forecast RMSE.

**Formula:**
```
SS = z × σ_d × sqrt(L)

where:
  z   = service level z-score (norm.ppf(service_level_target))
        A-class: 0.99 → z ≈ 2.326
        B-class: 0.95 → z ≈ 1.645
        C-class: 0.90 → z ≈ 1.282
  σ_d = daily demand standard deviation ≡ RMSE from DemandForecast.rmse
  L   = supplier lead time (days)
```

**Rationale for using RMSE as σ_d:**
- RMSE is computed in demand units (units/day), same as σ_d
- RMSE from walk-forward validation captures both model error and genuine demand variability
- Using RMSE directly avoids needing a separate std-dev estimate when forecast history exists
- For products without validation (C-class, RMSE=None): σ_d estimated as `avg_daily_demand × CV` using XYZ CV from Phase 3 classification

**Fallback when RMSE is unavailable:**
```python
if rmse is None:
    sigma_d = daily_demand_mean * demand_cv   # CV from ProductClassification
else:
    sigma_d = rmse
```

**Class `SafetyStockCalculator`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `compute(sigma_d, lead_time_days, service_level) -> float` | SS (units) | Main formula: `z × σ_d × sqrt(L)` |
| `get_z_score(service_level) -> float` | z | `scipy.stats.norm.ppf(service_level)` |
| `get_service_level_for_abc(abc_class) -> float` | service level | Lookup: A=0.99, B=0.95, C=0.90 |
| `estimate_sigma_from_cv(daily_mean, cv) -> float` | σ (units/day) | `daily_mean × cv`; used when RMSE unavailable |

---

#### 4.2.3 ROP Calculator (`src/optimization/rop_calculator.py`)

Computes the Reorder Point — the stock level at which a replenishment order must be triggered so that the order arrives before stock is exhausted.

**Formula:**
```
ROP = (avg_daily_demand × lead_time_days) + safety_stock

Demand during lead time:
  If DemandForecast.predicted_qty is available for the next lead_time_days days:
      demand_during_lt = SUM(predicted_qty[0:lead_time_days])   ← forecast-based
  Else:
      demand_during_lt = avg_daily_demand × lead_time_days      ← simple average
```

**Maximum Stock Level:**
```
max_stock = reorder_point + eoq
```

**Average Inventory:**
```
avg_inventory = safety_stock + eoq / 2
```

**Days of Supply at ROP trigger:**
```
days_supply_at_trigger = reorder_point / avg_daily_demand
```

**Class `ROPCalculator`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `compute(avg_daily_demand, lead_time_days, safety_stock) -> float` | ROP (units) | Main formula |
| `compute_forecast_based(forecast_series, lead_time_days, safety_stock) -> float` | ROP (units) | Uses sum of predicted_qty over lead_time_days; more accurate for trending demand |
| `compute_max_stock(rop, eoq) -> float` | max stock (units) | `ROP + EOQ` |
| `compute_avg_inventory(safety_stock, eoq) -> float` | avg inventory (units) | `SS + EOQ/2` |
| `compute_days_supply(current_stock, avg_daily_demand) -> Optional[float]` | days | `stock / demand`; None if demand=0 |

---

#### 4.2.4 Policy Engine (`src/optimization/policy_engine.py`)

Orchestrates the full portfolio inventory optimization run: retrieves forecasts and classifications, invokes all three calculators, persists results, and delegates alert generation.

**Class `PolicyEngine`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `run(forecast_run_id) -> OptimizationReport` | Full report | Main entry: processes all products, persists OptimizationRun + InventoryPolicy rows, delegates to AlertGenerator |
| `run_product(product_id) -> PolicyResult` | Single-product result | Computes policy without DB persistence; used for "what-if" parameter changes |
| `get_last_run_timestamp() -> Optional[datetime]` | datetime | MAX(run_timestamp) from optimization_runs |

**`run()` execution sequence:**
```
1. Retrieve latest ForecastRun and all DemandForecast rows
   → Raises ForecastRequiredError if no forecast run exists

2. Retrieve all ProductClassification records (latest per product)
   → Raises ClassificationRequiredError if no Phase 3 data exists

3. Retrieve current stock via InventoryService.get_stock_summary()

4. For each product (ABC priority order: A first):
   a. Look up DemandForecast rows (latest run, this product)
   b. Compute annual_demand = mean(predicted_qty) × 365
   c. Compute daily_demand_mean = mean(predicted_qty)
   d. Retrieve rmse from DemandForecast.rmse (None for C-class unvalidated)
   e. Retrieve lead_time_days from Supplier (product's primary supplier); default 7
   f. Retrieve ordering_cost from Supplier.ordering_cost_per_order; default DEFAULT_ORDERING_COST
   g. Compute holding_cost_per_unit = Product.cost_price × HOLDING_COST_RATE
   h. Look up service_level_target by abc_class (A=0.99, B=0.95, C=0.90)

   i. SafetyStockCalculator.compute(sigma_d, lead_time_days, service_level)
   j. EOQCalculator.compute(annual_demand, ordering_cost, holding_cost_per_unit)
   k. ROPCalculator.compute_forecast_based(forecast_series, lead_time_days, safety_stock)
   l. ROPCalculator.compute_max_stock(rop, eoq)
   m. EOQCalculator.compute_annual_ordering_cost(...)
   n. EOQCalculator.compute_annual_holding_cost(...)
   o. Collect PolicyResult

5. Create OptimizationRun header; flush for run_id
6. Bulk insert InventoryPolicy rows (one per product)
7. Delegate to AlertGenerator.generate(run_id, policies, current_stock)
8. Update OptimizationRun.alerts_generated count; commit
9. Return OptimizationReport
```

**`OptimizationReport` dataclass:**
```python
@dataclass
class OptimizationReport:
    run_id:               int
    run_timestamp:        datetime
    forecast_run_id:      Optional[int]
    total_products:       int
    policies_generated:   int
    alerts_generated:     int
    total_annual_cost:    float
    annual_cost_by_class: Dict[str, float]    # {"A": ..., "B": ..., "C": ...}
    alerts_by_severity:   Dict[str, int]      # {"CRITICAL": n, "HIGH": n, ...}
    policies:             List[PolicyResult]
    warnings:             List[str]
    duration_seconds:     float
```

---

#### 4.2.5 Alert Generator (`src/optimization/alert_generator.py`)

Compares current stock against each product's computed ROP and generates prioritized replenishment alerts.

**Alert Classification Logic:**

| Condition | Alert Type | Severity | Trigger |
|-----------|-----------|----------|---------|
| `current_stock == 0` | `STOCKOUT` | `CRITICAL` | No stock at all |
| `current_stock <= rop × APPROACHING_ROP_FRACTION` | `BELOW_ROP` | `CRITICAL` | At or below 50% of ROP for A-class |
| `current_stock <= rop` | `BELOW_ROP` | `HIGH` | At or below ROP |
| `current_stock <= rop × (1 + APPROACHING_ROP_BUFFER)` | `APPROACHING_ROP` | `MEDIUM` | Within 25% above ROP |
| `current_stock > max_stock` | `EXCESS` | `LOW` | Overstocked beyond max |

**Severity escalation for high-value (A-class) products:**
- A-class `BELOW_ROP` → `CRITICAL` (not `HIGH`)
- A-class `APPROACHING_ROP` → `HIGH` (not `MEDIUM`)

**Suggested Order Quantity:**
```python
suggested_qty = max(eoq, rop - current_stock + safety_stock)
# Order at least one EOQ; top up to max_stock if severely understocked
```

**Days Until Stockout:**
```python
if daily_demand_mean > 0:
    days_until_stockout = current_stock / daily_demand_mean
else:
    days_until_stockout = None  # zero demand; no stockout risk
```

**Class `AlertGenerator`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `generate(run_id, policies, current_stock_map) -> List[ReplenishmentAlert]` | alerts | Full portfolio alert scan; bulk inserts |
| `evaluate_product(policy, current_stock) -> Optional[ReplenishmentAlert]` | alert or None | Single-product check; returns None if stock is OK |
| `prioritize(alerts) -> List[ReplenishmentAlert]` | sorted alerts | CRITICAL first, then HIGH, then MEDIUM, then LOW; within severity by days_until_stockout ASC |

---

### 4.3 Optimization Service (`src/services/optimization_service.py`)

Query layer for optimization results — reads persisted policies and alerts, provides aggregated views for UI.

| Method | Returns | Description |
|--------|---------|-------------|
| `get_latest_policies() -> List[Dict]` | All products with latest policy | Joined with Product for name/SKU, ABC badge |
| `get_policy(product_id) -> Optional[Dict]` | Latest policy for one product | Full policy row with computed fields |
| `get_active_alerts(severity_filter) -> List[Dict]` | Unacknowledged alerts | Sorted CRITICAL→HIGH→MEDIUM→LOW; severity_filter optional |
| `get_alert_counts() -> Dict[str, int]` | `{"CRITICAL": n, "HIGH": n, ...}` | For Dashboard badge counts |
| `get_cost_summary() -> Dict` | Portfolio cost breakdown | `{"total": ..., "by_class": {...}, "holding": ..., "ordering": ...}` |
| `get_latest_run() -> Optional[OptimizationRun]` | Latest OptimizationRun | For timestamp display |
| `acknowledge_alert(alert_id, notes) -> None` | — | Sets `is_acknowledged=True`, `acknowledged_at=now()`, `acknowledged_by=notes` |
| `run_optimization(forecast_run_id) -> OptimizationReport` | Full report | Delegates to PolicyEngine.run() |

---

### 4.4 Presentation Layer

#### 4.4.1 Theme Extensions (`src/ui/theme.py`)

New alert severity and optimization color constants:

| Constant | Value | Usage |
|----------|-------|-------|
| `COLOR_ALERT_CRITICAL` | `"#d64545"` | CRITICAL alert row / badge (red) |
| `COLOR_ALERT_HIGH` | `"#e8a838"` | HIGH alert row / badge (amber) |
| `COLOR_ALERT_MEDIUM` | `"#5b8dee"` | MEDIUM alert row / badge (blue) |
| `COLOR_ALERT_LOW` | `"#6b7280"` | LOW alert row / badge (gray) |
| `COLOR_ROP_LINE` | `"#d64545"` | ROP marker on chart (red dashed) |
| `COLOR_SS_FILL` | `"#e8a838"` | Safety stock band fill (amber, 20% alpha) |
| `COLOR_COST_ORDERING` | `"#1f6aa5"` | Ordering cost bar segment (blue) |
| `COLOR_COST_HOLDING` | `"#2fa572"` | Holding cost bar segment (green) |

---

#### 4.4.2 ChartPanel Extension (`src/ui/components/chart_panel.py`)

New method:

```python
def plot_cost_breakdown(self, categories, ordering_costs, holding_costs, title):
    """
    Stacked bar chart: categories on x-axis (e.g. A / B / C or category names),
    ordering_costs and holding_costs as stack segments.
    Reference line at mean total cost.
    Used in OptimizationView cost analysis section.
    """
```

---

#### 4.4.3 FilterBar Extension (`src/ui/components/filter_bar.py`)

New optional controls (enabled via `show_optimization_filters=True`):

- **Service Level Override** `CTkOptionMenu`: ["Default (by ABC)", "90%", "95%", "99%"]
- **Lead Time Override** `CTkOptionMenu`: ["Default (from Supplier)", "3 days", "7 days", "14 days", "30 days"]
- `get_filters()` extended with `service_level_override: Optional[float]` and `lead_time_override: Optional[int]`

---

#### 4.4.4 Optimization View (`src/ui/views/optimization_view.py`)

New dedicated screen for inventory policy management:

```
┌──────────────────────────────────────────────────────────────────────┐
│  FILTER BAR  [Category ▼] [ABC Class ▼] [Service Level Override ▼]   │
│              [Lead Time Override ▼]                    [Optimize ↻]  │
├──────────────────────────────────────────────────────────────────────┤
│  SUMMARY CARDS                                                        │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐  ┌────────┐  │
│  │ Total Annual  │  │ Annual Holding │  │Annual Ordering│  │ Active │  │
│  │ Inventory Cost│  │   Cost         │  │     Cost      │  │ Alerts │  │
│  │  $248,342     │  │   $194,720     │  │   $53,622     │  │   3    │  │
│  └───────────────┘  └────────────────┘  └──────────────┘  └────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  COST BREAKDOWN CHART (left 45%)    │  POLICY TABLE (right 55%)       │
│  ┌──────────────────────────────┐   │  ┌──────┬──────┬──┬──┬───┬───┐  │
│  │  Stacked Bar: A / B / C      │   │  │ SKU  │ Name │AB│SS│ROP│EOQ│  │
│  │  ■ Ordering  ■ Holding       │   │  ├──────┼──────┼──┼──┼───┼───┤  │
│  │                              │   │  │SK020 │LED M │A │18│67 │45 │  │
│  │  A: $198K  B: $34K  C: $16K  │   │  │SK008 │Gad M │A │11│52 │38 │  │
│  │                              │   │  │SK010 │Gad U │A │ 0│ 0 │ 0 │  │
│  └──────────────────────────────┘   │  │ ...  │ ...  │..│..│...│...│  │
│                                     │  └──────┴──────┴──┴──┴───┴───┘  │
├──────────────────────────────────────────────────────────────────────┤
│  POLICY DETAIL PANEL (expanded on row click)                          │
│  SKU020 - LED Monitor (AX)  │  Service Level: 99%  │  Lead Time: 7d  │
│  ┌────────┬──────┬──────────┬────────┬─────────┬──────────────────┐  │
│  │   SS   │ ROP  │   EOQ    │  Max   │Ann. Cost│ Days Cover @ ROP │  │
│  │ 18 u   │ 67 u │  45 u   │ 112 u  │ $12,480 │    3.0 days      │  │
│  └────────┴──────┴──────────┴────────┴─────────┴──────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Five sections:**

1. **Filter Bar** with optimization-specific controls (service level override, lead time override, ABC class, category, "Run Optimization" button)
2. **Summary KPI Cards:** Total Annual Cost, Annual Holding Cost, Annual Ordering Cost, Active Alert Count (badge navigates to Alerts View)
3. **Cost Breakdown Chart + Policy Table** (side-by-side):
   - Left: `ChartPanel.plot_cost_breakdown()` stacked bar by ABC class or category
   - Right: `DataTable` with columns: SKU, Product Name, ABC, Lead Time (d), SS (u), ROP (u), EOQ (u), Max (u), Service Level, Annual Cost ($)
   - Row click expands a detail panel below with full policy metrics
4. **Policy Detail Panel** (shown on row click): full breakdown of all inputs and computed values for the selected product
5. **"No optimization run yet"** state: shown on initial load if `optimization_runs` table is empty; prompts "Run a forecast first, then click Optimize."

**Background thread implementation:**
```python
def _run_optimization(self):
    self._set_running_state(True)
    thread = threading.Thread(target=self._optimization_worker, daemon=True)
    thread.start()

def _optimization_worker(self):
    report = self.optimization_service.run_optimization(forecast_run_id=None)
    self.after(0, lambda: self._on_optimization_complete(report))
```

---

#### 4.4.5 Alerts View (`src/ui/views/alerts_view.py`)

Dedicated screen for monitoring and acknowledging active replenishment alerts:

```
┌──────────────────────────────────────────────────────────────────────┐
│  FILTER BAR  [Severity ▼]  [ABC Class ▼]  [Category ▼]              │
│  ● CRITICAL: 1   ● HIGH: 2   ○ MEDIUM: 0   ○ LOW: 0                 │
├──────────────────────────────────────────────────────────────────────┤
│  ACTIVE ALERTS TABLE                                                  │
│  ┌──────┬──────────────┬──┬──────────────┬───────┬─────┬───┬───────┐  │
│  │ SKU  │ Product      │AB│ Alert Type   │ Stock │ ROP │Sug│ Days  │  │
│  │      │              │  │              │ Units │     │Qty│ Left  │  │
│  ├──────┼──────────────┼──┼──────────────┼───────┼─────┼───┼───────┤  │
│  │SK010 │ Gadget Ultra │A │ ● STOCKOUT   │     0 │  46 │ 46│     0 │  │
│  │SK008 │ Gadget Max   │A │ ● BELOW_ROP  │    20 │  52 │ 38│   1.3 │  │
│  │SK011 │ Power Drill  │A │ ● BELOW_ROP  │    38 │  59 │ 32│   3.9 │  │
│  └──────┴──────────────┴──┴──────────────┴───────┴─────┴───┴───────┘  │
│                                [Acknowledge Selected]                  │
├──────────────────────────────────────────────────────────────────────┤
│  ALERT DETAIL PANEL (selected alert)                                  │
│  SKU010 - Gadget Ultra  │  STOCKOUT  │  CRITICAL                      │
│  Current: 0 u  │  ROP: 46 u  │  EOQ: 38 u  │  Lead Time: 7 days      │
│  Suggested Order: 46 units  │  Expected Arrival: 2026-02-27           │
│  Days Until Stockout: 0.0   │  Supplier: Acme Corp                   │
│  Notes: [________________________]   [Acknowledge]                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Three sections:**

1. **Filter Bar + Severity Counter Row**: severity filter dropdown; real-time colored counters (CRITICAL / HIGH / MEDIUM / LOW) updated on load
2. **Active Alerts Table**: unacknowledged alerts sorted by severity; columns: SKU, Product, ABC badge, Alert Type (colored badge), Current Stock, ROP, Suggested Order Qty, Days Until Stockout
   - Multi-select: checkboxes allow bulk acknowledgement
   - Row click expands detail panel
3. **Alert Detail Panel**: full context for selected alert — current vs. ROP vs. EOQ, expected arrival date (today + lead_time_days), supplier name, acknowledgement text field and button

---

#### 4.4.6 Dashboard View Extension (`src/ui/views/dashboard_view.py`)

New alert-focused elements added to the existing Dashboard:

**New KPI Cards (right side of existing KPI row, 3 new cards):**
| Card | Source | Color |
|------|--------|-------|
| Critical Alerts | `optimization.alert_counts["CRITICAL"]` | Danger red if > 0 |
| Below-ROP Products | `optimization.alert_counts["BELOW_ROP"]` | Amber if > 0 |
| Total Annual Inventory Cost | `optimization.total_annual_cost` | Neutral |

**Critical Alerts Strip** (new section between KPI cards and existing charts):
```
┌──────────────────────────────────────────────────────────────────────┐
│ REPLENISHMENT ALERTS:  ● CRITICAL: 1   ● HIGH: 2   [View All →]     │
│ SKU010 Gadget Ultra — STOCKOUT — Order 46 units NOW  [Acknowledge]  │
│ SKU008 Gadget Max   — BELOW_ROP — Order 38 units     [Acknowledge]  │
└──────────────────────────────────────────────────────────────────────┘
```
- Strip shows max 3 highest-priority alerts inline; "View All" button navigates to Alerts View
- Strip shows "No active alerts — inventory policies up to date ✓" when all acknowledged or no alerts

---

#### 4.4.7 Forecast View Extension (`src/ui/views/forecast_view.py`)

Existing Demand Adequacy Table gains two new columns:

| New Column | Source | Description |
|-----------|--------|-------------|
| ROP (units) | `InventoryPolicy.reorder_point` | Computed ROP for the product |
| EOQ (units) | `InventoryPolicy.eoq` | Suggested order size |

Row highlight rule: rows where `current_stock <= rop` are highlighted with severity color from theme (CRITICAL=red, HIGH=amber) — consistent with AlertsView.

---

#### 4.4.8 App Navigation (`src/ui/app.py`)

- Add **"Optimize"** nav button (6th button, between Forecast and Import)
- Add **"Alerts"** nav button (7th button, between Optimize and Import); displays alert count badge when `CRITICAL` or `HIGH` alerts exist
- `OptimizationView` and `AlertsView` instantiated lazily on first click
- Alert badge count refreshes when `AlertsView` acknowledges alerts

---

## 5. Data Flow

### 5.1 Optimization Run Sequence

```
User clicks "Optimize" in OptimizationView
    │
    ▼
OptimizationView._run_optimization()
    │ (background thread)
    ▼
PolicyEngine.run(forecast_run_id=latest)
    │
    ├── ForecastService.get_latest_run()          → ForecastRun (latest)
    │   └── Raises ForecastRequiredError if none
    │
    ├── ForecastService.get_accuracy_table()      → RMSE per product
    │
    ├── AnalyticsService.get_all_classifications() → ABC/XYZ + CV per product
    │   └── Raises ClassificationRequiredError if none
    │
    ├── InventoryService.get_stock_summary()       → Current stock per product
    │
    ├── For each product (ABC priority order):
    │       │
    │       ├── ForecastService.get_latest_forecast(product_id)
    │       │       └── List of predicted_qty per day (30 days)
    │       │
    │       ├── SafetyStockCalculator.compute(rmse, lead_time, service_level)
    │       │       └── float: safety stock (units)
    │       │
    │       ├── EOQCalculator.compute(annual_demand, ordering_cost, holding_cost)
    │       │       └── float: EOQ (units)
    │       │
    │       ├── ROPCalculator.compute_forecast_based(forecast_series, lead_time, ss)
    │       │       └── float: reorder point (units)
    │       │
    │       └── Collect PolicyResult (all computed fields)
    │
    ├── Persist OptimizationRun + InventoryPolicy rows
    │
    ├── AlertGenerator.generate(run_id, policies, current_stock_map)
    │       ├── Evaluate each product: current_stock vs ROP
    │       └── Persist ReplenishmentAlert rows for triggered conditions
    │
    └── Return OptimizationReport
            │ (main thread via after())
            ▼
    OptimizationView._on_optimization_complete(report)
        ├── Update KPI cards
        ├── Reload cost breakdown chart
        ├── Reload policy table
        └── Update nav alert badge count
```

### 5.2 Alert Acknowledgement Sequence

```
User clicks "Acknowledge" on alert row in AlertsView
    │
    ▼
AlertsView._on_acknowledge(alert_id, notes)
    │
    ├── OptimizationService.acknowledge_alert(alert_id, notes)
    │       └── UPDATE replenishment_alerts
    │           SET is_acknowledged=True,
    │               acknowledged_at=now(),
    │               acknowledged_by=notes
    │           WHERE id = alert_id
    │
    └── AlertsView._reload_alerts()
        ├── Update active alerts table (removes acknowledged row)
        ├── Update severity counters
        └── Notify app.py to refresh nav badge count
```

### 5.3 EOQ/ROP Worked Example (SKU020 LED Monitor)

```
Inputs:
  abc_class           = A
  lead_time_days      = 7                  (from Supplier record)
  forecast_horizon    = 30 days
  predicted_qty       = [22.4 units/day × 30 days]   (from SES model)
  rmse                = 2.0 units/day      (from DemandForecast.rmse)
  unit_cost           = $299.99            (from Product.cost_price)
  ordering_cost       = $50.00            (from Supplier.ordering_cost_per_order)
  holding_cost_rate   = 0.25              (HOLDING_COST_RATE constant)

Computed:
  annual_demand       = 22.4 × 365   = 8,176 units/year
  holding_cost_per_u  = $299.99×0.25 = $75.00/unit/year
  service_level       = 0.99         (A-class)
  z_score             = 2.326        (norm.ppf(0.99))

  SS  = 2.326 × 2.0 × sqrt(7)  = 2.326 × 2.0 × 2.646  = 12.3 → 13 units
  EOQ = sqrt(2 × 8,176 × 50 / 75) = sqrt(10,901) = 104.4 → 105 units
  ROP = SUM(predicted_qty[0:7]) + 13 = (22.4×7) + 13 = 156.8 + 13 = 169.8 → 170 units

  max_stock    = 170 + 105    = 275 units
  avg_inventory = 13 + 105/2  = 65.5 units

  annual_ordering_cost = (8,176 / 105) × $50   = 77.9 × $50   = $3,895
  annual_holding_cost  = 65.5 × $75            = $4,913
  annual_purchase_cost = 8,176 × $299.99       = $2,452,500
  total_annual_cost    = $3,895 + $4,913 + $2,452,500 = $2,461,308

Alert check:
  current_stock = 941 units   (from Phase 4 adequacy table)
  ROP = 170 units
  941 > 170 → No alert (stock well above ROP)
```

---

## 6. Optimization Model Details

### 6.1 Service Level Targets by ABC Class

| ABC Class | Service Level | z-Score | Interpretation |
|-----------|--------------|---------|---------------|
| A | 99% | 2.326 | Stockout acceptable 1 cycle in 100 — maximum protection for high-revenue products |
| B | 95% | 1.645 | Stockout acceptable 1 cycle in 20 — standard protection |
| C | 90% | 1.282 | Stockout acceptable 1 cycle in 10 — minimal protection; low-revenue products |

**Rationale:** Service levels are intentionally ABC-aligned. A-class products have the highest revenue impact per stockout event; over-protecting C-class products wastes capital in safety stock that could be better deployed elsewhere.

### 6.2 Holding Cost Rate

```
holding_cost_per_unit ($/unit/year) = unit_cost × HOLDING_COST_RATE
```

Default `HOLDING_COST_RATE = 0.25` (25% of unit cost per year), comprising:
- Capital cost (opportunity cost of cash tied up in inventory): ~12%
- Storage / warehousing cost: ~6%
- Insurance, taxes, and overhead: ~4%
- Obsolescence / spoilage risk: ~3%

This rate is a standard industry estimate. For Phase 5, it is a single configurable constant; Phase 6+ may introduce per-category rates.

### 6.3 EOQ Sensitivity Analysis

The EOQ formula is relatively insensitive to parameter errors (square-root dampening):

```
If D is estimated 20% high (too high):
  True EOQ / Wrong EOQ = sqrt(true_D / wrong_D) = sqrt(1/1.2) = 0.913
  Error in EOQ = 8.7% (not 20%)

Cost penalty of using wrong EOQ:
  Relative TAC increase = 0.5 × ((Q_wrong/Q_optimal) + (Q_optimal/Q_wrong)) - 1
  For 20% demand overestimate: penalty ≈ 0.4% of optimal TAC
```

This means moderate forecast errors do not significantly inflate total annual inventory cost — EOQ is robust to the ~11.9% portfolio MAPE achieved in Phase 4.

### 6.4 Safety Stock Sensitivity

Safety stock scales linearly with σ_d (RMSE) and with sqrt(lead_time):

```
SS = z × RMSE × sqrt(L)

Reducing lead time from 14 → 7 days:
  SS reduction = z × RMSE × (sqrt(14) - sqrt(7)) = z × RMSE × (3.742 - 2.646) = 29% reduction

Effect of RMSE improvement (11.9% → 8% MAPE):
  Approximate RMSE improvement: ~30%
  SS reduction: ~30% (linear relationship)
```

This quantifies the financial value of forecasting accuracy improvement: better Phase 4 models directly reduce Phase 5 safety stock and therefore annual holding cost.

### 6.5 Forecast-Based vs. Average-Based ROP

The `ROPCalculator` supports two modes:

**Simple (average-based):**
```
ROP = avg_daily_demand × L + SS
```

**Forecast-based (preferred):**
```
ROP = SUM(predicted_qty[0:L]) + SS
```

The forecast-based ROP captures trends during the lead time (e.g. a Holt's Linear product with rising demand has a higher ROP than its historical average would suggest). Products using Holt-Winters or Holt's Linear models benefit most from forecast-based ROP.

For C-class products without validation or with Croston's (constant rate): simple and forecast-based ROPs are identical.

---

## 7. New Configuration Constants (`config/constants.py`)

| Constant | Default | Description |
|----------|---------|-------------|
| `SERVICE_LEVEL_A` | 0.99 | Target service level for A-class products (99%) |
| `SERVICE_LEVEL_B` | 0.95 | Target service level for B-class products (95%) |
| `SERVICE_LEVEL_C` | 0.90 | Target service level for C-class products (90%) |
| `HOLDING_COST_RATE` | 0.25 | Fraction of unit cost charged as annual holding cost |
| `DEFAULT_ORDERING_COST` | 50.0 | Default cost per purchase order ($) if not set on Supplier |
| `DEFAULT_LEAD_TIME_DAYS` | 7 | Default supplier lead time (days) if not set on Supplier |
| `EOQ_MIN_ANNUAL_DEMAND` | 1.0 | Minimum annual demand (units) to compute meaningful EOQ |
| `EOQ_MIN_ORDER` | 1 | Minimum EOQ result; rounded up if EOQ < 1 |
| `APPROACHING_ROP_BUFFER` | 0.25 | Stock ≤ ROP × 1.25 triggers APPROACHING_ROP alert |
| `APPROACHING_ROP_FRACTION` | 0.50 | A-class: stock ≤ ROP × 0.50 escalates to CRITICAL |
| `MAX_STOCK_MULTIPLIER` | 1.0 | max_stock = ROP + EOQ × multiplier (default: 1.0 → ROP+EOQ) |
| `ALERT_DAYS_UNTIL_STOCKOUT_CRITICAL` | 3.0 | days_until_stockout ≤ 3 → CRITICAL regardless of class |
| `ALERT_DAYS_UNTIL_STOCKOUT_HIGH` | 7.0 | days_until_stockout ≤ 7 → HIGH severity minimum |
| `OPTIMIZATION_ABC_PRIORITY` | `["A","B","C"]` | Processing order within PolicyEngine.run() |

---

## 8. Technology Stack (Phase 5 Additions)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Statistical distributions | scipy | >= 1.10.0 | `norm.ppf()` for z-score lookup in SafetyStockCalculator (already declared in Phase 4) |

No new packages required. Phase 5 relies entirely on the existing stack (SQLAlchemy, numpy, scipy, customtkinter, matplotlib).

**Updated `requirements.txt`:**
```
# Phase 5 - Inventory Optimization
# (no new packages; scipy declared in Phase 4)
```

---

## 9. Implementation Tasks

### 9.1 Database Extension (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 1 | Add Phase 5 constants to `config/constants.py` | `config/constants.py` | 30 min |
| 2 | Extend `Supplier` model: `lead_time_days`, `ordering_cost_per_order` | `src/database/models.py` | 30 min |
| 3 | Add `OptimizationRun` ORM model + relationship to policies/alerts | `src/database/models.py` | 45 min |
| 4 | Add `InventoryPolicy` ORM model + 3 indexes | `src/database/models.py` | 1 hour |
| 5 | Add `ReplenishmentAlert` ORM model + 3 indexes | `src/database/models.py` | 45 min |

### 9.2 Optimization Engine (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 6 | Create `src/optimization/` package + `__init__.py` | `src/optimization/__init__.py` | 15 min |
| 7 | Implement `EOQCalculator` (Wilson formula + cost decomposition) | `src/optimization/eoq_calculator.py` | 2-3 hours |
| 8 | Implement `SafetyStockCalculator` (z-score × RMSE × sqrt(L); fallback to CV) | `src/optimization/safety_stock_calculator.py` | 2-3 hours |
| 9 | Implement `ROPCalculator` (forecast-based + average-based; max stock; days supply) | `src/optimization/rop_calculator.py` | 2-3 hours |
| 10 | Implement `PolicyEngine` (orchestrator; ABC-priority ordering; full persistence) | `src/optimization/policy_engine.py` | 4-5 hours |
| 11 | Implement `AlertGenerator` (alert type + severity logic; suggested qty; days until stockout) | `src/optimization/alert_generator.py` | 3-4 hours |

### 9.3 Service Layer (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 12 | Implement `OptimizationService` (full query layer + acknowledge) | `src/services/optimization_service.py` | 2-3 hours |
| 13 | Extend `KPIService` with `get_optimization_kpis()` + `get_all_kpis()` extension | `src/services/kpi_service.py` | 1 hour |

### 9.4 UI Extensions (Priority: Medium)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 14 | Add alert severity + optimization color constants to theme | `src/ui/theme.py` | 15 min |
| 15 | Add `plot_cost_breakdown()` to `ChartPanel` | `src/ui/components/chart_panel.py` | 1-2 hours |
| 16 | Extend `FilterBar` with service level + lead time override controls | `src/ui/components/filter_bar.py` | 45 min |
| 17 | Extend `ForecastView` adequacy table with ROP and EOQ columns + row highlighting | `src/ui/views/forecast_view.py` | 1-2 hours |
| 18 | Extend `DashboardView` with alert KPI cards + Critical Alerts strip | `src/ui/views/dashboard_view.py` | 2-3 hours |
| 19 | Implement `OptimizationView` (5 sections; background thread; detail panel) | `src/ui/views/optimization_view.py` | 5-6 hours |
| 20 | Implement `AlertsView` (alert table; severity counters; acknowledge flow) | `src/ui/views/alerts_view.py` | 4-5 hours |
| 21 | Extend `App` navigation: Optimize + Alerts buttons + alert badge count | `src/ui/app.py` | 45 min |

### 9.5 Testing (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 22 | EOQ Calculator tests (8 tests) | `tests/test_eoq_calculator.py` | 2-3 hours |
| 23 | Safety Stock Calculator tests (7 tests) | `tests/test_safety_stock_calculator.py` | 2 hours |
| 24 | ROP Calculator tests (7 tests) | `tests/test_rop_calculator.py` | 2 hours |
| 25 | Policy Engine tests (6 tests) | `tests/test_policy_engine.py` | 2-3 hours |
| 26 | Alert Generator tests (6 tests) | `tests/test_alert_generator.py` | 2 hours |
| 27 | Optimization Service integration tests (7 tests) | `tests/test_optimization_service.py` | 2-3 hours |

**Total estimated effort: 50-65 hours**

---

## 10. Implementation Order

The recommended build sequence verifies each calculator independently before integrating into the policy engine:

```
Step 1: Database Extension
  ├── Task 1:  Constants
  ├── Task 2:  Supplier model extension
  ├── Task 3:  OptimizationRun model
  ├── Task 4:  InventoryPolicy model + indexes
  └── Task 5:  ReplenishmentAlert model + indexes

Step 2: Optimization Engine (calculators first; verify each immediately)
  ├── Task 6:  Package + __init__.py
  ├── Task 7:  EOQCalculator
  ├── Task 22: EOQ tests                    ← verify immediately
  ├── Task 8:  SafetyStockCalculator
  ├── Task 23: Safety stock tests           ← verify immediately
  ├── Task 9:  ROPCalculator
  └── Task 24: ROP tests                   ← verify immediately

Step 3: Orchestration + Alerts
  ├── Task 10: PolicyEngine
  ├── Task 25: Policy engine tests          ← verify immediately
  ├── Task 11: AlertGenerator
  └── Task 26: Alert generator tests       ← verify immediately

Step 4: Service Layer
  ├── Task 12: OptimizationService
  ├── Task 13: KPIService extension
  └── Task 27: OptimizationService tests   ← verify immediately

Step 5: UI (build views last after logic is verified)
  ├── Task 14: Theme extensions
  ├── Task 15: ChartPanel.plot_cost_breakdown()
  ├── Task 16: FilterBar extensions
  ├── Task 17: ForecastView adequacy extension (ROP + EOQ columns)
  ├── Task 18: DashboardView alert extensions
  ├── Task 19: OptimizationView
  ├── Task 20: AlertsView
  └── Task 21: App nav extensions
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Forecast run not yet completed when user clicks "Optimize" | High | Medium | Guard in `PolicyEngine.run()` raises `ForecastRequiredError`; OptimizationView shows "Run a forecast first" prompt |
| `Product.cost_price` is NULL for some products (missing data) | High | Medium | `holding_cost_per_unit` defaults to `DEFAULT_ORDERING_COST × 0.5` when `cost_price` is None; policy_notes flagged as "estimated holding cost" |
| `Supplier.lead_time_days` not set for products linked to multiple suppliers or no supplier | Medium | Medium | Falls back to `DEFAULT_LEAD_TIME_DAYS` (7); policy_notes flagged as "default lead time used" |
| EOQ formula produces very large values for zero or near-zero demand (C-class slow movers) | Medium | High | `EOQ_MIN_ANNUAL_DEMAND` guard: if `annual_demand < 1.0`, EOQ set to 0 and ROP = safety_stock only; policy_notes flagged |
| Safety stock = 0 when RMSE = None and demand_cv = 0 (constant-demand C-class) | Low | Medium | Minimum safety stock floor: `max(SS, 1 unit)` for A/B class; C-class allows SS=0 |
| Alert count badge on nav button not refreshing after acknowledgement | Low | Medium | `AlertsView._on_acknowledge()` posts `APP_ALERT_REFRESH` event; `App` listens and re-queries `get_alert_counts()` |
| Optimization run on empty forecast table (no Phase 4 run) | High | Low | Guard: raises `ForecastRequiredError` with clear user message |
| Large portfolios (1,000+ products): PolicyEngine run time excessive | Medium | Low | All calculators are O(1) per product; bottleneck is DB reads. For 1,000 products: estimated < 5s |
| Inconsistency between Phase 4 adequacy status and Phase 5 ROP alerts | Low | Low | ForecastView adequacy uses coverage_days vs. thresholds; Phase 5 uses ROP triggers. Both shown side-by-side in updated ForecastView; documented difference in UI tooltip |

---

## 12. Testing Strategy

### 12.1 EOQ Calculator Tests (`tests/test_eoq_calculator.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_eoq_basic` | D=1000, S=50, H=10 | EOQ=sqrt(2×1000×50/10)=100 units |
| `test_eoq_cost_equality_at_optimum` | D=5000, S=80, H=20 | annual_ordering_cost ≈ annual_holding_cost (EOQ property) |
| `test_eoq_zero_demand` | D=0, S=50, H=10 | EOQ=0; no InvalidParameterError |
| `test_eoq_invalid_holding_cost` | H=0 | Raises `InvalidParameterError` |
| `test_eoq_invalid_ordering_cost` | S=0 | Raises `InvalidParameterError` |
| `test_eoq_fractional_result_rounded_up` | D=1, S=1, H=1 | EOQ=sqrt(2)≈1.41 → rounded up to 2 |
| `test_annual_ordering_cost` | D=1000, EOQ=100, S=50 | (1000/100)×50 = $500 |
| `test_total_annual_cost` | Known D, EOQ, SS, S, H, unit_cost | Sum = ordering + holding + purchase ✓ |

### 12.2 Safety Stock Calculator Tests (`tests/test_safety_stock_calculator.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_ss_basic` | σ_d=2.0, L=7, service=0.95 | SS=1.645×2.0×sqrt(7)=8.71 units |
| `test_ss_a_class_service` | abc="A" | `get_service_level_for_abc("A") == 0.99` |
| `test_ss_b_class_service` | abc="B" | `get_service_level_for_abc("B") == 0.95` |
| `test_ss_c_class_service` | abc="C" | `get_service_level_for_abc("C") == 0.90` |
| `test_ss_z_score_a_class` | service=0.99 | z ≈ 2.326 (± 0.001) |
| `test_ss_fallback_to_cv` | rmse=None, daily_mean=10, cv=0.5, L=7, service=0.95 | σ_d=5.0 → SS=1.645×5.0×sqrt(7)=21.77 units |
| `test_ss_zero_sigma` | σ_d=0.0, L=7 | SS=0.0 (no uncertainty → no buffer needed) |

### 12.3 ROP Calculator Tests (`tests/test_rop_calculator.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_rop_basic` | avg_demand=10, L=7, SS=15 | ROP=10×7+15=85 units |
| `test_rop_forecast_based` | forecast_series=[10]*7 + more, L=7, SS=15 | ROP=SUM([10]*7)+15=85 (same; flat demand) |
| `test_rop_forecast_based_trending` | forecast=[10,11,12,13,14,15,16]+more, L=7, SS=10 | ROP=SUM(10..16)+10=101 units (> simple average of 91) |
| `test_rop_max_stock` | ROP=85, EOQ=100 | max_stock=185 units |
| `test_rop_avg_inventory` | SS=15, EOQ=100 | avg_inventory=15+50=65 units |
| `test_days_supply_basic` | current_stock=70, avg_demand=10 | days_supply=7.0 |
| `test_days_supply_zero_demand` | avg_demand=0 | returns None (no consumption; no stockout risk) |

### 12.4 Policy Engine Tests (`tests/test_policy_engine.py`)

| Test | Scenario |
|------|----------|
| `test_run_persists_policies` | After `run()`, `inventory_policies` has 1 row per product in DB |
| `test_run_persists_optimization_run` | `optimization_runs` has 1 new row; `policies_generated` = product count |
| `test_run_abc_priority_order` | A-class products computed first (verified via run log) |
| `test_run_no_forecast_raises` | Empty `demand_forecasts` → `ForecastRequiredError` |
| `test_run_no_classification_raises` | Empty `product_classifications` → `ClassificationRequiredError` |
| `test_run_product_no_supplier` | Product with no linked supplier → uses `DEFAULT_LEAD_TIME_DAYS`; policy_notes flagged |

### 12.5 Alert Generator Tests (`tests/test_alert_generator.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_stockout_alert` | current_stock=0, ROP=50 | Alert type=STOCKOUT, severity=CRITICAL |
| `test_below_rop_alert_b_class` | current_stock=30, ROP=50, abc=B | Alert type=BELOW_ROP, severity=HIGH |
| `test_below_rop_alert_a_class_escalated` | current_stock=30, ROP=50, abc=A | Alert type=BELOW_ROP, severity=CRITICAL |
| `test_approaching_rop_alert` | current_stock=58, ROP=50 (58 ≤ 50×1.25=62.5) | Alert type=APPROACHING_ROP, severity=MEDIUM |
| `test_no_alert_when_stocked` | current_stock=200, ROP=50 | Returns None (no alert) |
| `test_suggested_order_qty` | ROP=50, EOQ=38, current_stock=20 | suggested_qty = max(38, 50-20+13) = max(38,43) = 43 units |

### 12.6 Optimization Service Tests (`tests/test_optimization_service.py`)

| Test | Scenario |
|------|----------|
| `test_run_optimization_persists` | After run, `optimization_runs` has 1 row; policies and alerts populated |
| `test_get_latest_policies` | Returns list with one dict per product; joined with Product name/SKU |
| `test_get_active_alerts_sorted` | Returns alerts CRITICAL first, then HIGH |
| `test_get_alert_counts` | Returns correct counts by severity |
| `test_acknowledge_alert` | After `acknowledge_alert(id, notes)`, alert `is_acknowledged=True` |
| `test_no_optimization_state` | `get_latest_policies()` on empty table returns `[]` without exception |
| `test_forecast_required_error` | `run_optimization()` without forecast data → `ForecastRequiredError` |

---

## 13. Non-Functional Requirements (Phase 5)

| Requirement | Target | Validation Method |
|-------------|--------|-------------------|
| Full portfolio optimization run time | < 5 seconds for 20 products | Profile with sample dataset; all calculations are O(1) per product |
| Full portfolio optimization run time (1,000 products) | < 30 seconds | Extrapolation; DB bulk insert dominates |
| Alert generation after optimization | < 1 second for 20 products | Separate timing measurement |
| Policy table render time | < 1 second | Customtkinter DataTable timing |
| Alert badge count refresh | < 200ms | In-memory query after acknowledge |
| OptimizationView "Run" without prior forecast | Immediate error banner | Manual test |
| Memory during optimization run | < 10 MB additional | No large in-memory structures; all DB-backed |

---

## 14. Phase 5 Exit Criteria

- [ ] `optimization_runs`, `inventory_policies`, `replenishment_alerts` tables created; schema migration verified
- [ ] `EOQCalculator.compute()` satisfies ordering cost = holding cost property at optimal Q (test: `test_eoq_cost_equality_at_optimum`)
- [ ] `SafetyStockCalculator` returns correct z-scores for A/B/C service levels (test: `test_ss_z_score_a_class`)
- [ ] `SafetyStockCalculator` falls back to CV-based σ_d when RMSE is None (test: `test_ss_fallback_to_cv`)
- [ ] `ROPCalculator` forecast-based mode correctly sums predicted_qty over lead time (test: `test_rop_forecast_based_trending`)
- [ ] `PolicyEngine.run()` processes all 20 products in ABC priority order; persists one InventoryPolicy row per product
- [ ] `PolicyEngine.run()` raises `ForecastRequiredError` when no DemandForecast data exists
- [ ] `AlertGenerator` correctly identifies STOCKOUT, BELOW_ROP, APPROACHING_ROP conditions; A-class escalation works
- [ ] `AlertGenerator` correctly computes `suggested_order_qty = max(EOQ, ROP - stock + SS)`
- [ ] `OptimizationService.acknowledge_alert()` sets `is_acknowledged=True` and persists timestamp
- [ ] OptimizationView renders all 5 sections (filter bar, KPI cards, cost chart, policy table, detail panel)
- [ ] AlertsView renders active alerts sorted by severity; acknowledging a row removes it from the table
- [ ] Dashboard shows Critical Alerts count KPI card and Critical Alerts strip with inline acknowledge
- [ ] ForecastView adequacy table shows ROP and EOQ columns; rows below ROP highlighted in severity color
- [ ] Navigation badge on "Alerts" button shows active alert count; refreshes after acknowledgement
- [ ] "Optimize" without prior forecast shows clear "Run a forecast first" banner (no crash)
- [ ] All 6 new test modules pass with 100% success
- [ ] Full 20-product optimization run completes in < 5 seconds

---

## 15. Transition to Phase 6

Phase 6 (Executive Dashboard & Reporting) will consume Phase 5 outputs for strategic summaries:

1. **Executive KPI Dashboard:**
   - `OptimizationService.get_cost_summary()` powers headline "Annual Inventory Investment" KPI
   - Alert counts by severity as risk indicator KPI cards
   - ABC-class cost breakdown chart embedded in executive summary page

2. **Automated Reporting:**
   - `InventoryPolicy` table provides data for "Inventory Policy Report" (PDF/Excel export):
     - Per-product: SS, ROP, EOQ, service level, annual cost
     - Portfolio: total cost, cost by class, alert summary
   - Phase 6 export engine reads `inventory_policies` directly; no additional service methods needed

3. **Trend Analysis:**
   - Multiple `OptimizationRun` rows enable trend views:
     - Total annual cost over time (has optimization become cheaper as forecasting improved?)
     - Alert count history (are we reducing recurring stockouts?)
   - Phase 6 may add a `compare_runs(run_id_1, run_id_2)` method to `OptimizationService`

4. **Supplier Performance Metrics:**
   - Phase 6 may extend `Supplier` model with `actual_lead_time_days` (recorded at receipt)
   - Variance between `lead_time_days` and actual → supplier reliability score
   - Feeds back into Phase 5 safety stock via dynamic lead time uncertainty: `SS = z × sqrt(L × σ_d² + D² × σ_L²)`

**Prerequisites from Phase 5:**
- `inventory_policies` table with `total_annual_cost`, `annual_ordering_cost`, `annual_holding_cost` per product per run
- `replenishment_alerts` table with `alert_type`, `severity`, `is_acknowledged` for alert history reports
- `OptimizationService.get_cost_summary()` providing aggregated cost breakdown
- `OptimizationService.get_active_alerts()` providing current risk status

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-20 | Initial Phase 5 implementation plan |

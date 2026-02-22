# Logistics DSS - Phase 3 Implementation Plan
# Analytics Engine

**Project:** Logistics Decision Support System
**Phase:** 3 of 8 - Analytics Engine
**Author:** Gilvan de Azevedo
**Date:** 2026-02-20
**Status:** Not Started
**Depends on:** Phase 2 (Basic Dashboard) -- functionally complete

---

## 1. Phase 3 Objective

Implement the core analytics engine that classifies inventory using the ABC and XYZ methodologies, computes detailed turnover metrics, and surfaces classification results across the dashboard UI. This phase transforms raw KPI data into actionable inventory intelligence, enabling managers to prioritize attention, optimize replenishment policies, and identify underperforming stock.

**Deliverables:**
- ABC Classification engine (Pareto-based revenue segmentation)
- XYZ Classification engine (demand variability / coefficient of variation)
- Combined ABC-XYZ matrix analysis
- Inventory Turnover Analyzer (by product, category, warehouse, period)
- Persistent classification storage in the database
- Analytics View (new screen with charts, matrices, and tables)
- Dashboard integration (classification badges, color-coded tables, updated KPI cards)
- Full test suite for all analytics calculations

---

## 2. Phase 2 Dependencies (Available)

Phase 3 builds directly on the following Phase 2 components:

| Component | Module | Usage in Phase 3 |
|-----------|--------|-------------------|
| InventoryService | `src/services/inventory_service.py` | Stock data for ABC/XYZ input |
| SalesService | `src/services/sales_service.py` | Revenue and demand history for classification |
| KPIService | `src/services/kpi_service.py` | Turnover inputs; extended with analytics KPIs |
| DataTable | `src/ui/components/data_table.py` | Extended with classification badge column |
| ChartPanel | `src/ui/components/chart_panel.py` | Extended with pie, matrix, and heatmap charts |
| FilterBar | `src/ui/components/filter_bar.py` | Extended with ABC/XYZ class filters |
| DashboardView | `src/ui/views/dashboard_view.py` | Receives classification badge integration |
| InventoryView | `src/ui/views/inventory_view.py` | Receives ABC/XYZ columns in product table |
| DatabaseManager | `src/database/connection.py` | Sessions for classification persistence |
| ORM Models | `src/database/models.py` | Extended with ProductClassification model |
| LoggerMixin | `src/logger.py` | Logging across all new modules |
| Constants | `config/constants.py` | Extended with classification thresholds |

---

## 3. Architecture Overview

### 3.1 Phase 3 Directory Structure

```
logistics-dss/
├── config/
│   ├── settings.py             # (existing)
│   └── constants.py            # + ABC/XYZ thresholds, classification constants
├── src/
│   ├── analytics/              # NEW: Analytics Engine
│   │   ├── __init__.py
│   │   ├── abc_classifier.py       # ABC classification (Pareto revenue analysis)
│   │   ├── xyz_classifier.py       # XYZ classification (demand variability)
│   │   ├── turnover_analyzer.py    # Inventory turnover analysis engine
│   │   └── classification_runner.py # Orchestrates full classification run
│   ├── services/               # (existing from Phase 2)
│   │   ├── inventory_service.py    # (existing)
│   │   ├── sales_service.py        # (existing)
│   │   ├── kpi_service.py          # + turnover analytics KPIs
│   │   └── analytics_service.py    # NEW: query layer for analytics results
│   ├── database/
│   │   ├── connection.py           # (existing)
│   │   └── models.py               # + ProductClassification model
│   ├── ui/
│   │   ├── app.py                  # + Analytics nav entry
│   │   ├── theme.py                # + classification color constants
│   │   ├── components/
│   │   │   ├── kpi_card.py         # (existing)
│   │   │   ├── data_table.py       # + badge column support
│   │   │   ├── chart_panel.py      # + pie chart, heatmap, matrix chart types
│   │   │   ├── filter_bar.py       # + ABC/XYZ class filter dropdowns
│   │   │   ├── status_bar.py       # (existing)
│   │   │   ├── import_dialog.py    # (existing)
│   │   │   └── classification_badge.py  # NEW: ABC/XYZ badge widget
│   │   └── views/
│   │       ├── dashboard_view.py   # + classification KPI cards + alert badges
│   │       ├── inventory_view.py   # + ABC/XYZ columns in product table
│   │       ├── import_view.py      # (existing)
│   │       └── analytics_view.py   # NEW: full analytics screen
├── tests/
│   ├── test_abc_classifier.py  # NEW: ABC classification tests
│   ├── test_xyz_classifier.py  # NEW: XYZ classification tests
│   ├── test_turnover.py        # NEW: Turnover analysis tests
│   └── test_analytics_service.py # NEW: Analytics service tests
└── main.py                     # (existing)
```

### 3.2 Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Presentation Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Dashboard   │  │  Inventory   │  │  Import  │  │ Analytics  │  │
│  │  View (+)    │  │  View (+)    │  │  View    │  │  View (NEW)│  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┘  └─────┬──────┘  │
│         │                 │                               │         │
│  ┌──────┴─────────────────┴───────────────────────────────┴───────┐  │
│  │           Reusable Components (+ extensions)                   │  │
│  │  KPI Card | Data Table (+) | Chart Panel (+) | Badge (NEW)    │  │
│  └──────────────────────────┬──────────────────────────────────── ┘  │
├─────────────────────────────┼───────────────────────────────────────┤
│                      Service Layer                                   │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────────┐  │
│  │  Inventory   │  │    Sales       │  │  Analytics Service (NEW) │  │
│  │  Service     │  │    Service     │  │  KPI Service (+)         │  │
│  └──────┬───────┘  └──────┬─────── ┘  └──────────┬───────────────┘  │
├─────────┴─────────────────┴──────────────────────┴─────────────────┤
│                     Analytics Engine (NEW)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  ABC         │  │   XYZ        │  │  Turnover                │   │
│  │  Classifier  │  │   Classifier │  │  Analyzer                │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘   │
│         └─────────────────┴──────────────────────┘                  │
│                  ClassificationRunner (orchestrator)                 │
├─────────────────────────────────────────────────────────────────────┤
│                     Data Layer (Phases 1 & 2)                        │
│  ┌──────────────┐  ┌──────────────────────────┐  ┌──────────────┐   │
│  │ Database     │  │  ORM Models              │  │  Importers   │   │
│  │ Manager      │  │  (+ ProductClassification│  │  (CSV/Excel) │   │
│  └──────────────┘  └──────────────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Database Model Extension

#### 4.1.1 ProductClassification (`src/database/models.py`)

New ORM model to persist classification results:

```python
class ProductClassification(Base):
    __tablename__ = "product_classifications"

    id              = Column(Integer, primary_key=True)
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=False)
    abc_class       = Column(String(1), nullable=False)   # "A", "B", or "C"
    xyz_class       = Column(String(1), nullable=False)   # "X", "Y", or "Z"
    abc_xyz_class   = Column(String(2), nullable=False)   # "AX", "AY", ..., "CZ"
    revenue_share   = Column(Float, nullable=False)       # % of total revenue
    cum_revenue_pct = Column(Float, nullable=False)       # cumulative % (for Pareto)
    demand_cv       = Column(Float, nullable=True)        # coefficient of variation
    avg_daily_demand= Column(Float, nullable=True)        # mean daily sales qty
    std_daily_demand= Column(Float, nullable=True)        # std dev of daily sales qty
    turnover_ratio  = Column(Float, nullable=True)        # COGS sold / avg inventory
    days_of_supply  = Column(Float, nullable=True)        # stock / avg daily demand
    lookback_days   = Column(Integer, nullable=False)     # analysis period used
    classified_at   = Column(DateTime, default=func.now())
    notes           = Column(Text, nullable=True)

    product = relationship("Product", back_populates="classifications")
```

**Indexes:**
- `(product_id, classified_at DESC)` -- latest classification per product
- `(abc_class, xyz_class)` -- filter by class combination

---

### 4.2 Analytics Engine

#### 4.2.1 ABC Classifier (`src/analytics/abc_classifier.py`)

**Purpose:** Segment products into A, B, and C tiers based on their cumulative revenue contribution (Pareto analysis).

**Algorithm:**

```
1. For each product, compute total revenue for the lookback period:
      revenue_i = SUM(quantity_sold * unit_price)
                  WHERE date >= (today - lookback_days)

2. Sort products by revenue_i descending.

3. Compute each product's revenue share:
      share_i = revenue_i / SUM(revenue_all)

4. Compute cumulative revenue percentage (rank order):
      cum_pct_i = SUM(share_j for j <= i)

5. Assign class by cumulative threshold:
      if cum_pct_i <= ABC_A_THRESHOLD  → class = "A"
      elif cum_pct_i <= ABC_B_THRESHOLD → class = "B"
      else                              → class = "C"
```

**Default thresholds (configurable via `config/constants.py`):**

| Constant | Default | Meaning |
|----------|---------|---------|
| `ABC_A_THRESHOLD` | 0.80 | Cumulative revenue up to 80% → class A |
| `ABC_B_THRESHOLD` | 0.95 | Cumulative revenue 80-95% → class B |

**Class definition:**

| Class | Revenue Contribution | Typical SKU Share | Strategic Focus |
|-------|---------------------|------------------|-----------------|
| A | Top 80% of revenue | ~20% of SKUs | Highest priority: tight control, frequent replenishment |
| B | Next 15% (80-95%) | ~30% of SKUs | Moderate priority: standard replenishment cycles |
| C | Bottom 5% (95-100%) | ~50% of SKUs | Low priority: simplified management, consider reduction |

**Class `ABCClassifier`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `classify(lookback_days)` | `List[ABCResult]` | Run full ABC classification for all products |
| `classify_product(product_id, lookback_days)` | `ABCResult` | Classify a single product |
| `get_distribution()` | `Dict[str, int]` | Count of products per class {A, B, C} |
| `get_revenue_summary()` | `Dict[str, float]` | Revenue total per class |

**`ABCResult` dataclass:**

```python
@dataclass
class ABCResult:
    product_id:      int
    product_sku:     str
    product_name:    str
    revenue:         float
    revenue_share:   float
    cum_revenue_pct: float
    abc_class:       str    # "A" | "B" | "C"
```

---

#### 4.2.2 XYZ Classifier (`src/analytics/xyz_classifier.py`)

**Purpose:** Segment products by demand variability using the Coefficient of Variation (CV) of historical daily sales quantities.

**Algorithm:**

```
1. For each product, collect daily sales quantity time series:
      daily_qty[date] = SUM(quantity_sold)
                        WHERE date >= (today - lookback_days)
                        AND product_id = ?

      Fill missing dates with 0 (no sales = 0 demand).

2. Compute statistics:
      mean_demand = MEAN(daily_qty)
      std_demand  = STD(daily_qty, ddof=1)

3. Compute Coefficient of Variation:
      CV = std_demand / mean_demand
           (CV = 0 if mean_demand = 0)

4. Assign class by CV threshold:
      if CV <  XYZ_X_THRESHOLD → class = "X"   (stable)
      elif CV < XYZ_Y_THRESHOLD → class = "Y"   (variable)
      else                      → class = "Z"   (highly variable)
```

**Default thresholds (configurable via `config/constants.py`):**

| Constant | Default | Meaning |
|----------|---------|---------|
| `XYZ_X_THRESHOLD` | 0.50 | CV < 0.50 → class X (low variability) |
| `XYZ_Y_THRESHOLD` | 1.00 | CV 0.50-1.00 → class Y (medium variability) |

**Class definition:**

| Class | CV Range | Demand Pattern | Forecasting Approach |
|-------|----------|----------------|---------------------|
| X | CV < 0.50 | Stable, predictable | High confidence forecasts; statistical methods |
| Y | 0.50 ≤ CV < 1.00 | Seasonal or trending | Moderate confidence; trend-adjusted models |
| Z | CV ≥ 1.00 | Erratic, unpredictable | Low confidence; safety stock buffers |

**Class `XYZClassifier`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `classify(lookback_days)` | `List[XYZResult]` | Run full XYZ classification for all products |
| `classify_product(product_id, lookback_days)` | `XYZResult` | Classify a single product |
| `get_distribution()` | `Dict[str, int]` | Count of products per class {X, Y, Z} |

**`XYZResult` dataclass:**

```python
@dataclass
class XYZResult:
    product_id:       int
    product_sku:      str
    product_name:     str
    avg_daily_demand: float
    std_daily_demand: float
    demand_cv:        float
    xyz_class:        str   # "X" | "Y" | "Z"
    data_points:      int   # number of days in analysis window
```

---

#### 4.2.3 Turnover Analyzer (`src/analytics/turnover_analyzer.py`)

**Purpose:** Compute inventory turnover ratios at product, category, and warehouse level, with period-over-period trend analysis.

**Turnover Calculation:**

```
COGS Sold (period):
    cogs_sold = SUM(quantity_sold * unit_cost)
                WHERE date BETWEEN period_start AND period_end

Average Inventory Value:
    avg_inventory = (value_at_period_start + value_at_period_end) / 2
    value_at_t    = SUM(quantity_on_hand * unit_cost) AT time t

Turnover Ratio:
    turnover = cogs_sold / avg_inventory
               (returns None if avg_inventory = 0)

Days Inventory Outstanding (DIO):
    DIO = period_length_days / turnover
```

**Class `TurnoverAnalyzer`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_product_turnover(product_id, days)` | `TurnoverResult` | Turnover for a single product |
| `get_all_product_turnovers(days)` | `List[TurnoverResult]` | Turnover for every product |
| `get_category_turnover(days)` | `List[Dict]` | Aggregated turnover by category |
| `get_warehouse_turnover(days)` | `List[Dict]` | Aggregated turnover by warehouse |
| `get_turnover_trend(product_id, periods)` | `List[TurnoverResult]` | Rolling period trend |
| `get_slow_movers(threshold, days)` | `List[TurnoverResult]` | Products below turnover threshold |
| `get_fast_movers(n, days)` | `List[TurnoverResult]` | Top N products by turnover |

**`TurnoverResult` dataclass:**

```python
@dataclass
class TurnoverResult:
    product_id:       int
    product_sku:      str
    product_name:     str
    category:         str
    turnover_ratio:   Optional[float]   # None if no inventory history
    dio_days:         Optional[float]   # Days Inventory Outstanding
    cogs_sold:        float
    avg_inventory_value: float
    period_days:      int
    period_start:     date
    period_end:       date
```

---

#### 4.2.4 Classification Runner (`src/analytics/classification_runner.py`)

**Purpose:** Orchestrates a full ABC+XYZ classification run, merges results into the combined ABC-XYZ matrix, persists to the database, and returns a summary report.

**Class `ClassificationRunner`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `run(lookback_days)` | `ClassificationReport` | Full ABC + XYZ + turnover run; persists results |
| `get_matrix_summary()` | `Dict[str, int]` | Product counts per ABC-XYZ cell |
| `get_last_run_timestamp()` | `Optional[datetime]` | When was the last classification run? |

**Combined Matrix (9-cell grid):**

```
         X (stable)    Y (variable)   Z (erratic)
    ┌──────────────┬──────────────┬──────────────┐
  A │  AX          │  AY          │  AZ          │
    │  High value  │  High value  │  High value  │
    │  Predictable │  Variable    │  Erratic     │
    ├──────────────┼──────────────┼──────────────┤
  B │  BX          │  BY          │  BZ          │
    │  Med value   │  Med value   │  Med value   │
    │  Predictable │  Variable    │  Erratic     │
    ├──────────────┼──────────────┼──────────────┤
  C │  CX          │  CY          │  CZ          │
    │  Low value   │  Low value   │  Low value   │
    │  Predictable │  Variable    │  Erratic     │
    └──────────────┴──────────────┴──────────────┘
```

**Strategic interpretation per cell:**

| Cell | Strategy |
|------|----------|
| AX | Critical, easy to manage. Tight replenishment, minimal safety stock |
| AY | Critical, needs buffer. Trend-adjusted replenishment + safety stock |
| AZ | Critical, unpredictable. High safety stock; monitor closely |
| BX | Standard management, predictable. Regular replenishment cycles |
| BY | Standard management, some variability. Moderate safety stock |
| BZ | Standard management, erratic. Review necessity; safety stock |
| CX | Low value, predictable. Simplified or consolidated ordering |
| CY | Low value, variable. Consider reducing SKU complexity |
| CZ | Low value, erratic. Strong candidate for discontinuation |

**`ClassificationReport` dataclass:**

```python
@dataclass
class ClassificationReport:
    run_timestamp:   datetime
    lookback_days:   int
    total_products:  int
    abc_distribution: Dict[str, int]    # {"A": 45, "B": 68, "C": 137}
    xyz_distribution: Dict[str, int]    # {"X": 80, "Y": 90, "Z": 80}
    matrix_counts:   Dict[str, int]     # {"AX": 30, "AY": 10, ..., "CZ": 20}
    revenue_by_class: Dict[str, float]  # {"A": 850000.0, "B": ...}
    results:         List[ProductClassificationRecord]
    warnings:        List[str]          # e.g. "50 products had no sales data"
```

---

### 4.3 Analytics Service (`src/services/analytics_service.py`)

**Purpose:** Query layer for analytics data -- reads classification results from the database, provides filtered and aggregated views for the UI.

| Method | Returns | Description |
|--------|---------|-------------|
| `get_all_classifications(lookback_days)` | `List[Dict]` | All product classifications (latest run) |
| `get_by_abc_class(cls, lookback_days)` | `List[Dict]` | Products filtered by ABC class |
| `get_by_xyz_class(cls, lookback_days)` | `List[Dict]` | Products filtered by XYZ class |
| `get_by_matrix_cell(abc, xyz)` | `List[Dict]` | Products in a specific ABC-XYZ cell |
| `get_matrix_counts()` | `Dict[str, int]` | Product count per matrix cell |
| `get_revenue_by_class()` | `Dict[str, float]` | Revenue totals per ABC class |
| `get_last_classification_timestamp()` | `Optional[datetime]` | Time of most recent run |
| `get_slow_movers(threshold)` | `List[Dict]` | Products with turnover below threshold |
| `run_classification(lookback_days)` | `ClassificationReport` | Trigger a new classification run |

---

### 4.4 Presentation Layer Extensions

#### 4.4.1 Theme Extensions (`src/ui/theme.py`)

New classification color constants:

| Constant | Value | Usage |
|----------|-------|-------|
| `COLOR_CLASS_A` | "#2fa572" | Class A badge (high value — green) |
| `COLOR_CLASS_B` | "#e8a838" | Class B badge (medium value — amber) |
| `COLOR_CLASS_C` | "#6b7280" | Class C badge (low value — gray) |
| `COLOR_CLASS_X` | "#1f6aa5" | Class X badge (stable — blue) |
| `COLOR_CLASS_Y` | "#9b59b6" | Class Y badge (variable — purple) |
| `COLOR_CLASS_Z` | "#d64545" | Class Z badge (erratic — red) |

#### 4.4.2 Classification Badge (`src/ui/components/classification_badge.py`)

A compact, color-coded widget that renders an ABC, XYZ, or combined ABC-XYZ label:

```
  ┌───┐ ┌───┐     ┌────┐
  │ A │ │ X │  or │ AX │
  └───┘ └───┘     └────┘
  green  blue    combined
```

**Properties:**
- `abc_class`: "A" | "B" | "C" | None
- `xyz_class`: "X" | "Y" | "Z" | None
- `mode`: "abc" | "xyz" | "combined"
- `size`: "small" | "normal" (for table vs. detail panel use)
- Tooltip on hover showing full class description

#### 4.4.3 Chart Panel Extensions (`src/ui/components/chart_panel.py`)

New chart types to add to the existing ChartPanel:

| New Method | Description |
|------------|-------------|
| `plot_pie(labels, values, title)` | ABC/XYZ class distribution pie chart |
| `plot_matrix_heatmap(matrix_data, title)` | 3×3 ABC-XYZ matrix with count/revenue shading |
| `plot_grouped_bar(categories, series, title)` | Multi-series bar (e.g., ABC count by warehouse) |
| `plot_turnover_trend(periods, values, title)` | Period-over-period turnover line chart |

#### 4.4.4 Filter Bar Extensions (`src/ui/components/filter_bar.py`)

New filter controls added to the existing FilterBar:

- **ABC Class** dropdown: All / A / B / C
- **XYZ Class** dropdown: All / X / Y / Z
- **ABC-XYZ Cell** dropdown: All / AX / AY / ... / CZ (optional, for analytics view)

---

### 4.5 Analytics View (`src/ui/views/analytics_view.py`)

The new dedicated analytics screen, accessible from the navigation sidebar:

```
┌──────────────────────────────────────────────────────────────────────┐
│  FILTER BAR  [Category ▼]  [Warehouse ▼]  [Period: 30 days ▼]       │
│              [ABC Class ▼]  [XYZ Class ▼]     [Run Analysis ↻]       │
├──────────────────────────────────────────────────────────────────────┤
│  SUMMARY CARDS                                                        │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────────┐  │
│  │  A items  │  │  B items  │  │  C items  │  │  Last Analysis    │  │
│  │    45     │  │    68     │  │   137     │  │  2026-02-20 14:30 │  │
│  │  80% rev  │  │  15% rev  │  │   5% rev  │  │  250 products     │  │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │  ABC-XYZ MATRIX (heatmap)  │  │  ABC Distribution (pie)          │ │
│  │                             │  │                                  │ │
│  │       X      Y      Z       │  │        ██ A (18%)                │ │
│  │  A  [ 30 ] [ 10 ] [  5 ]   │  │     ████ B (27%)                 │ │
│  │  B  [ 40 ] [ 18 ] [ 10 ]   │  │  ███████ C (55%)                 │ │
│  │  C  [ 60 ] [ 45 ] [ 32 ]   │  │                                  │ │
│  └─────────────────────────────┘  └──────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  PRODUCT CLASSIFICATION TABLE                                    │  │
│  │  ┌──────┬──────────────┬────────┬──────┬──────┬────────┬───────┐  │  │
│  │  │ SKU  │ Name         │ ABC    │ XYZ  │ Rev% │ CV     │ Turn  │  │  │
│  │  ├──────┼──────────────┼────────┼──────┼──────┼────────┼───────┤  │  │
│  │  │SK001 │ Widget A     │ [A]    │ [X]  │ 8.2% │ 0.21   │ 4.3x  │  │  │
│  │  │SK002 │ Widget B     │ [A]    │ [Y]  │ 6.1% │ 0.74   │ 3.8x  │  │  │
│  │  │SK003 │ Gadget C     │ [C]    │ [Z]  │ 0.2% │ 1.82   │ 0.4x  │  │  │
│  │  │ ...  │ ...          │  ...   │  ... │  ... │  ...   │  ...  │  │  │
│  │  └──────┴──────────────┴────────┴──────┴──────┴────────┴───────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Responsibilities:**
- Render summary KPI cards for ABC class distribution
- Display 3×3 ABC-XYZ heatmap matrix with product counts and revenue shading
- Render ABC and XYZ distribution pie charts
- Display full product classification table with sortable columns and badge widgets
- Trigger classification run via "Run Analysis" button with progress feedback
- Show "No analysis run yet" state if no classifications exist in the database
- React to filter bar changes (category, warehouse, class filters)

---

### 4.6 Dashboard View Integration (`src/ui/views/dashboard_view.py`)

Extensions to the existing dashboard:

1. **New KPI Cards (right section):**
   - Class A SKU Count
   - Class C Slow Movers Count (turnover < threshold)
   - Average Portfolio Turnover

2. **Low Stock Alert Table Extension:**
   - Add ABC/XYZ badge column to the existing alert table
   - Sort: AZ and BZ stockouts first (high-value, erratic demand)

3. **Classification Summary Strip** (below KPI row):
   ```
   ┌──────────────────────────────────────────────────────────────┐
   │ ABC:  [A] 45 items  [B] 68 items  [C] 137 items              │
   │ XYZ:  [X] 80 items  [Y] 90 items  [Z] 80 items               │
   └──────────────────────────────────────────────────────────────┘
   ```

---

### 4.7 Inventory View Integration (`src/ui/views/inventory_view.py`)

Extensions to the existing inventory table:

1. Add **ABC** and **XYZ** columns to the product data table
2. Add **Turnover** and **DIO (days)** columns
3. Extend FilterBar with ABC/XYZ class dropdowns
4. Row color coding:
   - CZ products: subtle red row tint (low value, erratic)
   - AZ products: subtle amber row tint (high value, erratic — needs attention)
5. Product detail panel extended with:
   - Classification section showing ABC, XYZ badges and interpretation
   - Turnover trend mini-chart (last 4 periods)

---

## 5. Data Flow

### 5.1 Classification Run Sequence

```
User clicks "Run Analysis" in Analytics View / first app launch
    │
    ▼
AnalyticsView._run_classification(lookback_days=30)
    │
    ▼
ClassificationRunner.run(lookback_days=30)
    │
    ├── SalesService.get_sales_by_period()       → revenue data for ABC
    │
    ├── ABCClassifier.classify(30)
    │       ├── Compute revenue per product
    │       ├── Sort descending by revenue
    │       ├── Compute cumulative % (Pareto)
    │       └── Assign A / B / C                 → List[ABCResult]
    │
    ├── SalesService.get_daily_sales_summary()   → daily demand series for XYZ
    │
    ├── XYZClassifier.classify(30)
    │       ├── Build daily qty time series per product
    │       ├── Fill missing dates with 0
    │       ├── Compute mean and std dev
    │       ├── Compute CV = std / mean
    │       └── Assign X / Y / Z                 → List[XYZResult]
    │
    ├── TurnoverAnalyzer.get_all_product_turnovers(30)
    │       └── Compute turnover ratio + DIO     → List[TurnoverResult]
    │
    ├── Merge ABC + XYZ + Turnover by product_id
    │       └── Compute abc_xyz_class (e.g., "AX")
    │
    ├── Persist to product_classifications table
    │
    └── Return ClassificationReport
            │
            ▼
    AnalyticsView.refresh() -- update all charts, matrix, table
    DashboardView.refresh() -- update classification strip + alert badges
    InventoryView.refresh() -- update table with new ABC/XYZ columns
```

### 5.2 Analytics Filter Sequence

```
User selects ABC Class = "A" in Analytics View filter bar
    │
    ▼
FilterBar.on_filter_change(abc_class="A")
    │
    ▼
AnalyticsView._apply_filters(abc_class="A")
    │
    ├── AnalyticsService.get_by_abc_class("A")   → filtered product list
    ├── Recompute matrix counts for filtered set
    ├── Update pie chart for filtered subset
    └── Reload product classification table with filtered rows
```

### 5.3 Turnover Trend Sequence

```
User clicks a product row in Inventory View (or Analytics View)
    │
    ▼
InventoryView._show_product_detail(product_id)
    │
    ├── TurnoverAnalyzer.get_turnover_trend(product_id, periods=6)
    │       └── Computes turnover for 6 consecutive 30-day windows
    │
    └── ChartPanel.plot_turnover_trend(periods, ratios, title)
            └── Renders mini line chart in detail panel
```

---

## 6. Analytics Calculation Details

### 6.1 ABC Classification: Worked Example

Given 5 products with 30-day revenue:

| Product | Revenue | Revenue Share | Cumulative % | Class |
|---------|---------|---------------|--------------|-------|
| SKU001 | $50,000 | 50.0% | 50.0% | A |
| SKU002 | $20,000 | 20.0% | 70.0% | A |
| SKU003 | $10,000 | 10.0% | 80.0% | A |
| SKU004 | $ 8,000 |  8.0% | 88.0% | B |
| SKU005 | $ 7,000 |  7.0% | 95.0% | B |
| SKU006 | $ 3,000 |  3.0% | 98.0% | C |
| SKU007 | $ 2,000 |  2.0% | 100.0% | C |

Total: $100,000. SKUs 001-003 contribute 80% → class A. SKUs 004-005 bring cumulative to 95% → class B. Remainder → class C.

**Products with zero revenue** are automatically assigned class C.

### 6.2 XYZ Classification: Worked Example

Daily sales for SKU001 over 7 days: [10, 12, 11, 9, 10, 13, 11]

```
mean = (10+12+11+9+10+13+11) / 7 = 10.86
std  = STDEV([10,12,11,9,10,13,11]) ≈ 1.35
CV   = 1.35 / 10.86 ≈ 0.124  → Class X (stable)
```

Daily sales for SKU003 over 7 days: [0, 50, 0, 0, 75, 0, 0]

```
mean = (0+50+0+0+75+0+0) / 7 ≈ 17.86
std  ≈ 29.73
CV   = 29.73 / 17.86 ≈ 1.66  → Class Z (erratic)
```

**Products with no sales data** (all zeros) receive CV = 0 and class X by default, but are flagged in `ClassificationReport.warnings`.

**Minimum data requirement:** At least `XYZ_MIN_DATA_POINTS` (default: 7) days of data. Products below this are classified as Z and flagged.

### 6.3 Turnover Analysis: Period Windows

For trend analysis (`get_turnover_trend`), the lookback window is divided into N equal consecutive periods:

```
total_window = N * period_days

Period 1: (today - N*period_days) to (today - (N-1)*period_days)
Period 2: (today - (N-1)*period_days) to (today - (N-2)*period_days)
...
Period N: (today - period_days) to today
```

Default: 6 periods × 30 days = 180 days of turnover trend history.

### 6.4 Slow Mover Detection

A product is flagged as a **slow mover** when:

```
turnover_ratio < SLOW_MOVER_THRESHOLD   (default: 1.0)
```

A turnover ratio of less than 1.0 means the inventory value exceeds the cost of goods sold over the period -- the product is not selling fast enough to justify its holding cost.

**Slow mover risk score** (composite):

```
risk_score = (1 / turnover_ratio) * cv * (1 + (C_class_weight if class=C else 0))
```

Higher risk score = stronger candidate for markdown, discontinuation, or reorder suspension.

---

## 7. New Configuration Constants (`config/constants.py`)

| Constant | Default | Description |
|----------|---------|-------------|
| `ABC_A_THRESHOLD` | 0.80 | Cumulative revenue threshold for class A |
| `ABC_B_THRESHOLD` | 0.95 | Cumulative revenue threshold for class B |
| `XYZ_X_THRESHOLD` | 0.50 | CV upper bound for class X (stable) |
| `XYZ_Y_THRESHOLD` | 1.00 | CV upper bound for class Y (variable) |
| `XYZ_MIN_DATA_POINTS` | 7 | Minimum days of sales data for XYZ classification |
| `SLOW_MOVER_THRESHOLD` | 1.0 | Turnover ratio below which a product is "slow" |
| `FAST_MOVER_TOP_N` | 10 | Top N products shown in fast-mover report |
| `TURNOVER_TREND_PERIODS` | 6 | Number of periods for trend analysis |
| `TURNOVER_TREND_PERIOD_DAYS` | 30 | Days per trend period |
| `DEFAULT_CLASSIFICATION_LOOKBACK` | 30 | Default lookback for classification runs |
| `AUTO_CLASSIFY_ON_IMPORT` | False | Trigger classification automatically after data import |

---

## 8. Technology Stack (Phase 3 Additions)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Statistical analysis | numpy | >= 1.24.0 | CV computation, statistical functions |
| Data manipulation | pandas | >= 2.0.0 | Time series aggregation for XYZ (already in requirements) |

**Updated `requirements.txt`:**

```
# Phase 1 - Data Processing
pandas>=2.0.0
openpyxl>=3.1.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0

# Phase 2 - Dashboard UI
customtkinter>=5.2.0
matplotlib>=3.7.0
babel>=2.12.0

# Phase 3 - Analytics Engine
numpy>=1.24.0

# Testing
pytest>=8.0.0
pytest-cov>=4.0.0

# Development (optional)
black>=23.0.0
isort>=5.12.0
mypy>=1.0.0
```

> **Note:** `numpy` may already be installed as a transitive dependency of `pandas` and `matplotlib`. Declaring it explicitly pins the minimum version.

---

## 9. Implementation Tasks

### 9.1 Database Extension (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 1 | Add `ProductClassification` ORM model | `src/database/models.py` | 1 hour |
| 2 | Create and test migration (add new table) | `src/database/connection.py` | 30 min |

### 9.2 Analytics Engine (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 3 | Create `src/analytics/` package structure | `src/analytics/__init__.py` | 15 min |
| 4 | Implement `ABCClassifier` | `src/analytics/abc_classifier.py` | 3-4 hours |
| 5 | Implement `XYZClassifier` | `src/analytics/xyz_classifier.py` | 3-4 hours |
| 6 | Implement `TurnoverAnalyzer` | `src/analytics/turnover_analyzer.py` | 3-4 hours |
| 7 | Implement `ClassificationRunner` (merge + persist) | `src/analytics/classification_runner.py` | 3-4 hours |
| 8 | Add Phase 3 constants to configuration | `config/constants.py` | 30 min |

### 9.3 Service Layer (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 9 | Implement `AnalyticsService` (query layer) | `src/services/analytics_service.py` | 2-3 hours |
| 10 | Extend `KPIService` with analytics KPIs | `src/services/kpi_service.py` | 1-2 hours |

### 9.4 UI Extensions (Priority: Medium)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 11 | Add classification color constants to theme | `src/ui/theme.py` | 15 min |
| 12 | Implement `ClassificationBadge` widget | `src/ui/components/classification_badge.py` | 2 hours |
| 13 | Extend `ChartPanel` with pie, heatmap, grouped bar, trend | `src/ui/components/chart_panel.py` | 3-4 hours |
| 14 | Extend `FilterBar` with ABC/XYZ class dropdowns | `src/ui/components/filter_bar.py` | 1-2 hours |
| 15 | Implement `AnalyticsView` (matrix, charts, table) | `src/ui/views/analytics_view.py` | 6-8 hours |
| 16 | Add Analytics nav entry to main app | `src/ui/app.py` | 30 min |
| 17 | Extend `DashboardView` (badges, classification strip) | `src/ui/views/dashboard_view.py` | 2-3 hours |
| 18 | Extend `InventoryView` (ABC/XYZ columns, row tinting, detail panel) | `src/ui/views/inventory_view.py` | 3-4 hours |

### 9.5 Testing (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 19 | ABC Classifier unit tests (known Pareto inputs) | `tests/test_abc_classifier.py` | 3-4 hours |
| 20 | XYZ Classifier unit tests (known CV inputs) | `tests/test_xyz_classifier.py` | 3-4 hours |
| 21 | Turnover Analyzer unit tests (known COGS/inventory) | `tests/test_turnover.py` | 2-3 hours |
| 22 | Analytics Service integration tests | `tests/test_analytics_service.py` | 2-3 hours |

**Total estimated effort: ~50-65 hours**

---

## 10. Implementation Order

The recommended build sequence verifies each engine independently before integration:

```
Step 1: Database Extension
  ├── Task 1: ProductClassification model
  └── Task 2: Schema migration

Step 2: Analytics Engine (pure Python -- no UI dependency)
  ├── Task 3: Package structure + constants (Task 8)
  ├── Task 4: ABCClassifier
  ├── Task 19: ABC tests          ← verify immediately
  ├── Task 5: XYZClassifier
  ├── Task 20: XYZ tests          ← verify immediately
  ├── Task 6: TurnoverAnalyzer
  ├── Task 21: Turnover tests     ← verify immediately
  └── Task 7: ClassificationRunner (merge + persist)

Step 3: Service Layer
  ├── Task 9:  AnalyticsService
  ├── Task 10: KPIService extensions
  └── Task 22: Analytics service tests

Step 4: UI Components
  ├── Task 11: Theme extensions
  ├── Task 12: ClassificationBadge
  ├── Task 13: ChartPanel extensions
  └── Task 14: FilterBar extensions

Step 5: Views
  ├── Task 15: AnalyticsView
  ├── Task 16: Nav entry
  ├── Task 17: DashboardView extensions
  └── Task 18: InventoryView extensions
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Products with no sales data skew XYZ to X | Medium | High | Flag zero-demand products separately; assign Z with warning, not X |
| Small data windows produce unreliable CV | High | Medium | Enforce `XYZ_MIN_DATA_POINTS`; flag and skip products below threshold |
| Classification run blocks UI thread on large datasets | High | High | Run `ClassificationRunner.run()` in a background thread; show progress dialog |
| ABC thresholds don't reflect actual business Pareto | Medium | Medium | Make thresholds configurable via constants; document how to tune |
| Pivot table / matrix heatmap Matplotlib rendering slow | Low | Medium | Cache the last rendered figure; only re-render on new data |
| Re-running classification creates unbounded history rows | Medium | Low | Keep only the latest N runs per product (configurable); prune on each run |
| InventoryView row tinting conflicts with existing zero-stock highlighting | Medium | Medium | Define clear priority rules: stockout highlight > CZ tint |

---

## 12. Testing Strategy

### 12.1 ABC Classifier Tests (`tests/test_abc_classifier.py`)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_abc_basic_pareto` | 7 products with known revenues | Correct A/B/C assignment by cumulative % |
| `test_abc_all_equal_revenue` | All products same revenue | All assigned C (each adds tiny % to cumulative) except possibly first few |
| `test_abc_single_product` | 1 product | Classified as A (it alone = 100% of revenue) |
| `test_abc_zero_revenue_product` | 1 product with $0 sales | Assigned C; does not affect other products' classification |
| `test_abc_custom_thresholds` | Custom A=0.70, B=0.90 | Correct class boundaries shift accordingly |
| `test_abc_distribution_counts` | Known dataset | `get_distribution()` returns correct count per class |
| `test_abc_revenue_summary` | Known dataset | Revenue total per class matches input sums |

### 12.2 XYZ Classifier Tests (`tests/test_xyz_classifier.py`)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_xyz_stable_demand` | Daily qty: [10,10,10,10,10,10,10] | CV=0.0 → class X |
| `test_xyz_high_variability` | Daily qty: [0,50,0,0,100,0,0] | CV > 1.0 → class Z |
| `test_xyz_medium_variability` | Daily qty: [5,15,8,12,6,14,10] | 0.5 ≤ CV < 1.0 → class Y |
| `test_xyz_zero_demand_product` | Daily qty: [0,0,0,0,0,0,0] | CV=0, flagged in warnings, assigned Z |
| `test_xyz_insufficient_data` | Fewer than `XYZ_MIN_DATA_POINTS` | Flagged; assigned Z with warning |
| `test_xyz_missing_dates_filled` | Sparse sales records | Missing dates correctly filled with 0 |
| `test_xyz_custom_thresholds` | Custom X=0.3, Y=0.7 | Boundaries applied correctly |

### 12.3 Turnover Analyzer Tests (`tests/test_turnover.py`)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_turnover_basic` | COGS=$1,000 / avg inventory=$500 | turnover=2.0, DIO=15 days (30-day period) |
| `test_turnover_zero_inventory` | Avg inventory = $0 | turnover=None (undefined) |
| `test_turnover_zero_sales` | COGS = $0 | turnover=0.0, DIO=None (infinite) |
| `test_turnover_category_aggregation` | 3 products in "Widgets" category | Aggregated correctly at category level |
| `test_turnover_trend` | 6 periods, known COGS per period | Correct ratio sequence returned |
| `test_slow_mover_detection` | threshold=1.0; products with ratio 0.4, 2.1, 0.9 | Returns products with ratios 0.4 and 0.9 |

### 12.4 Analytics Service Tests (`tests/test_analytics_service.py`)

End-to-end tests using a seeded test database:

| Test | Scenario |
|------|----------|
| `test_run_classification_persists` | Run → rows exist in `product_classifications` |
| `test_get_by_abc_class_filters` | After run, filter by "A" returns only A-class products |
| `test_matrix_counts_correct` | Matrix count dict sums to total product count |
| `test_no_classification_state` | Query on empty DB returns empty list gracefully |
| `test_multiple_runs_latest_used` | Two runs; service returns data from most recent |

---

## 13. Non-Functional Requirements (Phase 3)

| Requirement | Target | Validation Method |
|-------------|--------|-------------------|
| Classification run time | < 5 seconds for 10,000 SKUs | Profile with synthetic dataset |
| Analytics View load time | < 2 seconds (from cached classification) | Profiling |
| Chart render time (heatmap) | < 1 second | Matplotlib render timing |
| Memory overhead of classification | < 50 MB additional | Process memory monitoring |
| Background thread safety | No UI freeze during classification run | Manual testing; thread-safe DB session |
| Classification persistence | Survives app restart | Integration test: run, restart, verify data |

---

## 14. Phase 3 Exit Criteria

- [ ] `ProductClassification` table created and populated after classification run
- [ ] ABC Classifier correctly segments products with known Pareto inputs (all tests pass)
- [ ] XYZ Classifier correctly computes CV and assigns classes (all tests pass)
- [ ] Turnover Analyzer returns correct ratios and DIO values (all tests pass)
- [ ] `ClassificationRunner` merges ABC + XYZ + turnover and persists results
- [ ] `AnalyticsService` returns filtered classification data correctly
- [ ] Analytics View renders: 3×3 ABC-XYZ heatmap matrix, distribution pie charts, product classification table
- [ ] "Run Analysis" button triggers background classification and refreshes the view
- [ ] Dashboard View shows classification summary strip (A/B/C and X/Y/Z counts)
- [ ] Dashboard View low-stock alert table shows ABC/XYZ badges per product
- [ ] Inventory View shows ABC and XYZ columns with badge widgets
- [ ] Inventory View detail panel shows classification info and turnover trend chart
- [ ] FilterBar supports filtering by ABC class and XYZ class in both Inventory and Analytics views
- [ ] "No analysis run yet" state handled gracefully in Analytics View
- [ ] All 4 new test modules pass with 100% success rate
- [ ] Classification run completes in < 5 seconds with 1,000 products

---

## 15. Transition to Phase 4

Phase 4 (Demand Forecasting) will directly consume Phase 3 outputs:

1. **XYZ segments guide model selection** -- X products use statistical methods (exponential smoothing, ARIMA); Y products use trend-adjusted methods; Z products use safety-stock-based rules rather than point forecasts.
2. **ABC segments prioritize forecast effort** -- A products get detailed, individually tuned models; C products get simple average-based estimates.
3. **Turnover data provides baseline demand rates** -- average daily demand computed in XYZ classification feeds directly into forecasting model initialization.
4. **Analytics View extended** -- Phase 4 adds a Forecast panel to the Analytics View, showing predicted vs. actual demand per product class.

**Prerequisites from Phase 3:**
- `ProductClassification` table with ABC, XYZ, avg_daily_demand, and demand_cv columns
- `AnalyticsService.get_all_classifications()` providing the full classified product list
- `TurnoverAnalyzer.get_all_product_turnovers()` for baseline demand estimation
- Functional Analytics View for surfacing forecast results alongside classification data

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-20 | Initial Phase 3 implementation plan |

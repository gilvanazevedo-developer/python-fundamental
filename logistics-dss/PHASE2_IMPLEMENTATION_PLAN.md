# Logistics DSS - Phase 2 Implementation Plan
# Basic Dashboard

**Project:** Logistics Decision Support System
**Phase:** 2 of 8 - Basic Dashboard
**Author:** Gilvan de Azevedo
**Date:** 2026-02-19
**Status:** Not Started
**Depends on:** Phase 1 (Core Data Layer) -- functionally complete

---

## 1. Phase 2 Objective

Build the first visual layer of the application: a desktop dashboard that surfaces inventory KPIs, stock-level tables, and summary panels. This phase transforms raw data (imported in Phase 1) into actionable operational information for Inventory Managers.

**Deliverables:**
- Desktop application window using CustomTkinter
- Operational dashboard with stock-level table and filters
- KPI summary cards (stock health, service level, financial)
- Data query/service layer between UI and database
- Embedded chart panel (Matplotlib)
- Data refresh and import trigger from the UI

---

## 2. Phase 1 Dependencies (Available)

Phase 2 builds directly on the following Phase 1 components:

| Component | Module | Usage in Phase 2 |
|-----------|--------|-------------------|
| DatabaseManager | `src/database/connection.py` | Query sessions for all dashboard reads |
| Product model | `src/database/models.py` | SKU listing, cost/price data |
| Warehouse model | `src/database/models.py` | Location filtering |
| InventoryLevel model | `src/database/models.py` | Current stock quantities |
| SalesRecord model | `src/database/models.py` | Sales history for KPI computation |
| Supplier model | `src/database/models.py` | Lead time data (days of supply) |
| CSVImporter | `src/importer/csv_importer.py` | Import trigger from dashboard |
| ExcelImporter | `src/importer/excel_importer.py` | Import trigger from dashboard |
| LoggerMixin | `src/logger.py` | Logging across all new modules |
| Settings | `config/settings.py` | Paths, configuration values |

---

## 3. Architecture Overview

### 3.1 Phase 2 Directory Structure

```
logistics-dss/
├── config/
│   ├── settings.py             # + UI settings (window size, theme, refresh)
│   └── constants.py            # + KPI thresholds, dashboard constants
├── src/
│   ├── services/               # NEW: Business logic / query layer
│   │   ├── __init__.py
│   │   ├── inventory_service.py    # Stock queries, inventory aggregations
│   │   ├── sales_service.py        # Sales queries, period aggregations
│   │   └── kpi_service.py          # KPI calculations engine
│   ├── ui/                     # NEW: Desktop user interface
│   │   ├── __init__.py
│   │   ├── app.py                  # Main application window + navigation
│   │   ├── theme.py                # Color palette, fonts, style constants
│   │   ├── components/             # Reusable UI widgets
│   │   │   ├── __init__.py
│   │   │   ├── kpi_card.py         # Single KPI metric card widget
│   │   │   ├── data_table.py       # Sortable, filterable data table
│   │   │   ├── chart_panel.py      # Matplotlib chart container
│   │   │   ├── filter_bar.py       # Category/warehouse filter controls
│   │   │   ├── status_bar.py       # Bottom bar (DB status, record counts)
│   │   │   └── import_dialog.py    # File import dialog
│   │   └── views/                  # Screen-level layouts
│   │       ├── __init__.py
│   │       ├── dashboard_view.py   # Main operational dashboard
│   │       ├── inventory_view.py   # Detailed inventory table view
│   │       └── import_view.py      # Data import management view
│   ├── database/               # (existing from Phase 1)
│   ├── importer/               # (existing from Phase 1)
│   └── validator/              # (existing from Phase 1)
├── tests/
│   ├── test_services.py        # NEW: Service layer tests
│   ├── test_kpi.py             # NEW: KPI calculation tests
│   └── test_ui.py              # NEW: UI component tests (non-visual)
├── assets/                     # NEW: Static assets
│   └── icons/                  # Application icons (optional)
└── main.py                     # NEW: Application entry point
```

### 3.2 Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                           │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │  Dashboard   │  │  Inventory   │  │  Import              │  │
│   │  View        │  │  View        │  │  View                │  │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│          │                 │                      │              │
│   ┌──────┴─────────────────┴──────────────────────┴───────────┐  │
│   │              Reusable Components                          │  │
│   │  KPI Card | Data Table | Chart Panel | Filter Bar         │  │
│   └──────────────────────────┬────────────────────────────────┘  │
├──────────────────────────────┼──────────────────────────────────┤
│                     Service Layer                                │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │  Inventory   │  │   Sales      │  │   KPI                │  │
│   │  Service     │  │   Service    │  │   Service            │  │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
├──────────┴─────────────────┴──────────────────────┴─────────────┤
│                     Data Layer (Phase 1)                         │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │ Database     │  │  ORM         │  │  Importers           │  │
│   │ Manager      │  │  Models      │  │  (CSV/Excel)         │  │
│   └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Service Layer

The service layer sits between the UI and the database. It encapsulates all SQLAlchemy queries and business calculations so the UI never interacts with the ORM directly.

#### 4.1.1 InventoryService (`src/services/inventory_service.py`)

**Purpose:** Query and aggregate inventory data for display.

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_all_products()` | `List[Dict]` | All products with current stock levels joined |
| `get_stock_by_warehouse(warehouse_id)` | `List[Dict]` | Stock levels for a specific warehouse |
| `get_stock_by_product(product_id)` | `List[Dict]` | Stock across all warehouses for a product |
| `get_stock_summary()` | `Dict` | Total SKUs, total units, total value, items at zero |
| `get_low_stock_items(threshold)` | `List[Dict]` | Products below a quantity threshold |
| `get_categories()` | `List[str]` | Distinct product categories for filtering |
| `get_warehouses()` | `List[Dict]` | All warehouses with id, name, location |
| `search_products(query)` | `List[Dict]` | Search products by name or ID substring |

**Key query patterns:**
```python
# Stock with product details (JOIN)
session.query(Product, InventoryLevel)
    .join(InventoryLevel, Product.id == InventoryLevel.product_id)
    .all()

# Total inventory value (aggregate)
session.query(
    func.sum(InventoryLevel.quantity * Product.unit_cost)
).join(Product).scalar()
```

#### 4.1.2 SalesService (`src/services/sales_service.py`)

**Purpose:** Query and aggregate sales data for KPIs and charts.

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_sales_by_period(start, end)` | `List[Dict]` | Sales records within a date range |
| `get_daily_sales_summary(days)` | `List[Dict]` | Daily totals for the last N days |
| `get_sales_by_product(product_id)` | `List[Dict]` | Sales history for a specific product |
| `get_sales_by_category(days)` | `List[Dict]` | Revenue by category for period |
| `get_top_products(n, days)` | `List[Dict]` | Top N products by revenue or quantity |
| `get_total_revenue(days)` | `Decimal` | Total revenue for the last N days |
| `get_average_daily_demand(product_id, days)` | `float` | Mean daily quantity sold |

#### 4.1.3 KPIService (`src/services/kpi_service.py`)

**Purpose:** Compute all dashboard KPIs from inventory and sales data.

**KPI Definitions:**

| KPI | Category | Formula | Unit |
|-----|----------|---------|------|
| **Total SKUs** | Stock Health | `COUNT(DISTINCT products.id)` | count |
| **Total Units in Stock** | Stock Health | `SUM(inventory_levels.quantity)` | units |
| **Total Inventory Value** | Financial | `SUM(quantity * unit_cost)` | currency |
| **Total Retail Value** | Financial | `SUM(quantity * unit_price)` | currency |
| **Days of Supply** | Stock Health | `current_stock / avg_daily_demand` | days |
| **Inventory Turnover** | Stock Health | `total_sold_cost / avg_inventory_value` | ratio |
| **Stockout Count** | Service Level | `COUNT(products WHERE quantity = 0)` | count |
| **Stockout Rate** | Service Level | `stockout_count / total_SKUs * 100` | % |
| **Fill Rate** | Service Level | `(orders_filled / total_orders) * 100` | % |
| **Carrying Cost** | Financial | `avg_inventory_value * carrying_rate` | currency |
| **Average Unit Cost** | Financial | `total_inventory_value / total_units` | currency |
| **Potential Margin** | Financial | `total_retail_value - total_inventory_value` | currency |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_stock_health_kpis()` | `Dict[str, Any]` | Total SKUs, units, days of supply, turnover |
| `get_service_level_kpis()` | `Dict[str, Any]` | Stockout count/rate, fill rate |
| `get_financial_kpis()` | `Dict[str, Any]` | Inventory value, carrying cost, margin |
| `get_all_kpis()` | `Dict[str, Any]` | Combined dictionary of all KPIs |
| `get_product_kpis(product_id)` | `Dict[str, Any]` | KPIs for a single product |
| `get_warehouse_kpis(warehouse_id)` | `Dict[str, Any]` | KPIs for a single warehouse |

**Configurable Constants (to add to `config/constants.py`):**

| Constant | Default | Description |
|----------|---------|-------------|
| `CARRYING_COST_RATE` | 0.25 (25%) | Annual carrying cost as % of inventory value |
| `DEFAULT_LOOKBACK_DAYS` | 30 | Default period for sales-based KPIs |
| `LOW_STOCK_THRESHOLD` | 10 | Default "low stock" quantity threshold |
| `STOCKOUT_THRESHOLD` | 0 | Quantity at or below which product is "out" |
| `DAYS_OF_SUPPLY_WARNING` | 7 | Days of supply below which to flag warning |
| `DAYS_OF_SUPPLY_CRITICAL` | 3 | Days of supply below which to flag critical |

---

### 4.2 Presentation Layer (UI)

#### 4.2.1 Application Entry Point (`main.py`)

```python
# main.py - Application launcher
from src.ui.app import LogisticsDSSApp

def main():
    app = LogisticsDSSApp()
    app.mainloop()

if __name__ == "__main__":
    main()
```

- Initializes DatabaseManager and creates tables if needed
- Creates the main application window
- Starts the CustomTkinter event loop

#### 4.2.2 Main Application (`src/ui/app.py`)

**Responsibilities:**
- Create the root `customtkinter.CTk` window
- Set window title, size, and appearance mode (dark/light)
- Build navigation sidebar with view switching
- Manage view lifecycle (create, show, hide, refresh)
- Handle application-level events (close, resize)

**Window Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Logistics DSS                                    [Dark/Light]  │
├────────┬────────────────────────────────────────────────────────┤
│        │                                                        │
│  NAV   │              MAIN CONTENT AREA                         │
│        │                                                        │
│ [Dash] │  ┌──────────────────────────────────────────────────┐  │
│ [Inv]  │  │  Content from active view                        │  │
│ [Imp]  │  │  (DashboardView / InventoryView / ImportView)    │  │
│        │  │                                                  │  │
│        │  │                                                  │  │
│        │  └──────────────────────────────────────────────────┘  │
│        │                                                        │
├────────┴────────────────────────────────────────────────────────┤
│  Status: Connected | Products: 150 | Last Import: 2026-02-19   │
└─────────────────────────────────────────────────────────────────┘
```

**UI Configuration (to add to `config/settings.py`):**

| Setting | Default | Description |
|---------|---------|-------------|
| `WINDOW_TITLE` | "Logistics DSS" | Window title |
| `WINDOW_WIDTH` | 1280 | Default window width (px) |
| `WINDOW_HEIGHT` | 720 | Default window height (px) |
| `WINDOW_MIN_WIDTH` | 1024 | Minimum window width (px) |
| `WINDOW_MIN_HEIGHT` | 600 | Minimum window height (px) |
| `APPEARANCE_MODE` | "dark" | CustomTkinter appearance (dark/light/system) |
| `COLOR_THEME` | "blue" | CustomTkinter color theme |
| `AUTO_REFRESH_SECONDS` | 0 | Auto-refresh interval (0 = disabled) |
| `NAV_WIDTH` | 180 | Navigation sidebar width (px) |

#### 4.2.3 Theme (`src/ui/theme.py`)

Centralized style constants for consistent look:

| Constant | Value | Usage |
|----------|-------|-------|
| `COLOR_PRIMARY` | "#1f6aa5" | Buttons, active nav, accents |
| `COLOR_SUCCESS` | "#2fa572" | Positive KPIs, success states |
| `COLOR_WARNING` | "#e8a838" | Warning thresholds, caution |
| `COLOR_DANGER` | "#d64545" | Stockouts, critical alerts |
| `COLOR_NEUTRAL` | "#6b7280" | Secondary text, borders |
| `COLOR_BG_CARD` | "#2b2b2b" (dark) / "#ffffff" (light) | KPI card backgrounds |
| `FONT_HEADER` | ("Segoe UI", 18, "bold") | Section headers |
| `FONT_KPI_VALUE` | ("Segoe UI", 28, "bold") | Large KPI numbers |
| `FONT_KPI_LABEL` | ("Segoe UI", 11) | KPI descriptions |
| `FONT_TABLE` | ("Consolas", 11) | Table data |
| `CARD_CORNER_RADIUS` | 10 | KPI card rounding |
| `CARD_PADDING` | 15 | Internal card padding |

#### 4.2.4 Reusable Components

**KPI Card (`src/ui/components/kpi_card.py`)**

A self-contained widget displaying a single metric:
```
┌─────────────────────┐
│  Total Units         │  ← label (FONT_KPI_LABEL)
│  24,580             │  ← value (FONT_KPI_VALUE, colored)
│  ▲ 5.2% vs last mo  │  ← trend (optional, green/red)
└─────────────────────┘
```

**Properties:**
- `label`: metric name
- `value`: current value (auto-formatted: numbers, currency, percentages)
- `trend`: optional delta vs. previous period (with up/down indicator)
- `color`: value color (success/warning/danger based on thresholds)
- `update(value, trend)`: refresh displayed data

**Data Table (`src/ui/components/data_table.py`)**

Scrollable table built on `CTkScrollableFrame` with Treeview:
```
┌─────────────────────────────────────────────────────────────┐
│  SKU     │ Name          │ Category │ Stock │ Value    │ ▲▼ │
├──────────┼───────────────┼──────────┼───────┼──────────┤    │
│  SKU001  │ Widget A      │ Widgets  │  150  │ $1,575   │    │
│  SKU002  │ Widget B      │ Widgets  │   42  │ $630     │    │
│  SKU003  │ Gadget C      │ Gadgets  │    0  │ $0       │ !! │
│  ...     │               │          │       │          │    │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Column sorting (click header to toggle asc/desc)
- Row selection with event callback
- Configurable columns (name, width, alignment, formatter)
- Row highlighting for zero-stock items (danger color)
- Pagination or virtual scrolling for 10,000+ rows
- `load_data(rows)`: populate table from list of dicts
- `clear()`: remove all rows
- `get_selected()`: return selected row data

**Chart Panel (`src/ui/components/chart_panel.py`)**

Matplotlib figure embedded in CustomTkinter via `FigureCanvasTkAgg`:

**Chart types supported:**
- Bar chart: stock levels by category or warehouse
- Line chart: daily sales trend over time
- Horizontal bar: top 10 products by stock value

**Properties:**
- `figure_size`: (width, height) in inches
- `plot_bar(labels, values, title)`: render bar chart
- `plot_line(x, y, title, xlabel, ylabel)`: render line chart
- `plot_horizontal_bar(labels, values, title)`: render h-bar
- `clear()`: clear current plot
- `refresh()`: redraw canvas

**Filter Bar (`src/ui/components/filter_bar.py`)**

Horizontal control strip for filtering dashboard data:
```
┌──────────────────────────────────────────────────────────────┐
│  Category: [All ▼]  Warehouse: [All ▼]  Search: [________]  │
│  Period: [Last 30 days ▼]                     [Refresh ↻]    │
└──────────────────────────────────────────────────────────────┘
```

**Controls:**
- Category dropdown (populated from `InventoryService.get_categories()`)
- Warehouse dropdown (populated from `InventoryService.get_warehouses()`)
- Search text entry (triggers `InventoryService.search_products()`)
- Period selector (7 / 14 / 30 / 60 / 90 days)
- Refresh button (triggers full data reload)
- `on_filter_change` callback: notifies parent view to re-query

**Status Bar (`src/ui/components/status_bar.py`)**

Bottom bar showing application state:
```
┌──────────────────────────────────────────────────────────────┐
│  DB: Connected  │  Products: 1,250  │  Last refresh: 14:32  │
└──────────────────────────────────────────────────────────────┘
```

**Import Dialog (`src/ui/components/import_dialog.py`)**

Modal dialog for triggering data imports:
- File picker (CSV/Excel filter)
- Data type selector dropdown (Products, Inventory, Sales, Suppliers, Warehouses)
- Import button with progress feedback
- Result summary (records imported, errors)
- Uses `CSVImporter` / `ExcelImporter` from Phase 1

#### 4.2.5 Views

**Dashboard View (`src/ui/views/dashboard_view.py`)**

The main operational screen. Layout:
```
┌──────────────────────────────────────────────────────────────────┐
│  FILTER BAR                                                      │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ Total    │ Total    │ Inventory│ Stockout │ Days of  │ Carrying │
│ SKUs     │ Units    │ Value    │ Rate     │ Supply   │ Cost     │
│ 1,250    │ 24,580   │ $142K    │ 3.2%     │ 18 days  │ $35.5K   │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────┤
│                                                                  │
│  ┌─────────────────────────────┐  ┌────────────────────────────┐ │
│  │  Stock by Category (bar)    │  │  Daily Sales Trend (line)  │ │
│  │                             │  │                            │ │
│  │  ████ Widgets     1,200     │  │  ──────────────────────    │ │
│  │  ███  Gadgets       800     │  │                            │ │
│  │  ██   Tools         350     │  │                            │ │
│  └─────────────────────────────┘  └────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  LOW STOCK ALERTS                                            │ │
│  │  SKU003 - Gadget C         │  0 units  │  !! OUT OF STOCK   │ │
│  │  SKU017 - Widget X         │  5 units  │  ! LOW STOCK       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**Responsibilities:**
- Compose KPI cards, chart panels, and alert table
- Call `KPIService.get_all_kpis()` on load and refresh
- Call `SalesService.get_daily_sales_summary()` for trend chart
- Call `InventoryService.get_low_stock_items()` for alerts
- React to filter bar changes by re-querying with parameters

**Inventory View (`src/ui/views/inventory_view.py`)**

Detailed stock table with full product listing:
```
┌──────────────────────────────────────────────────────────────────┐
│  FILTER BAR                                                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DATA TABLE                                                      │
│  ┌──────┬──────────────┬──────────┬─────┬──────────┬──────────┐  │
│  │ SKU  │ Product Name │ Category │ Qty │ Cost     │ Value    │  │
│  ├──────┼──────────────┼──────────┼─────┼──────────┼──────────┤  │
│  │ ...  │ ...          │ ...      │ ... │ ...      │ ...      │  │
│  └──────┴──────────────┴──────────┴─────┴──────────┴──────────┘  │
│                                                                  │
│  Showing 1-50 of 1,250 products                    [< 1 2 3 >]  │
│                                                                  │
│  ── PRODUCT DETAIL (on row click) ──────────────────────────────  │
│  SKU001 - Widget A                                               │
│  Stock: 150 units across 2 warehouses                            │
│  Avg Daily Sales: 8.3 units | Days of Supply: 18                 │
│  WH001 (Main): 100 units | WH002 (East): 50 units               │
└──────────────────────────────────────────────────────────────────┘
```

**Responsibilities:**
- Full product table with sortable columns
- Row click → detail panel showing per-warehouse breakdown
- Filter by category, warehouse, search text
- Pagination for large datasets
- Export current view (future: Phase 1 remaining task)

**Import View (`src/ui/views/import_view.py`)**

Data import management screen:
```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  IMPORT DATA                                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Data Type:  [Products ▼]                                  │  │
│  │  File:       [Browse...]  products_2026.csv                │  │
│  │                                          [Import]          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  IMPORT HISTORY                                                  │
│  ┌──────────────┬──────────┬───────┬────────┬────────┬────────┐  │
│  │ File         │ Type     │ Total │ OK     │ Errors │ Status │  │
│  ├──────────────┼──────────┼───────┼────────┼────────┼────────┤  │
│  │ products.csv │ Products │ 100   │ 98     │ 2      │ Partial│  │
│  │ sales.xlsx   │ Sales    │ 5000  │ 5000   │ 0      │ Success│  │
│  └──────────────┴──────────┴───────┴────────┴────────┴────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Responsibilities:**
- File selection with native file dialog
- Data type mapping
- Import execution using Phase 1 importers
- Progress feedback (record count, status)
- Import history table from `import_logs` table

---

## 5. Data Flow

### 5.1 Dashboard Load Sequence

```
User opens app / clicks "Dashboard" / clicks "Refresh"
    │
    ▼
DashboardView.refresh()
    │
    ├── KPIService.get_all_kpis()
    │       ├── InventoryService.get_stock_summary()  → stock health cards
    │       ├── SalesService.get_total_revenue(30)    → financial cards
    │       └── Compute derived KPIs                  → service level cards
    │
    ├── SalesService.get_daily_sales_summary(30)      → line chart data
    │
    ├── InventoryService.get_stock_summary_by_category() → bar chart data
    │
    └── InventoryService.get_low_stock_items(10)      → alert table
            │
            ▼
        UI updates (KPI cards, charts, table)
```

### 5.2 Filter Change Sequence

```
User selects Category = "Widgets" in filter bar
    │
    ▼
FilterBar.on_filter_change(category="Widgets")
    │
    ▼
DashboardView._apply_filters(category="Widgets")
    │
    ├── KPIService.get_all_kpis(category="Widgets")
    ├── SalesService.get_daily_sales_summary(30, category="Widgets")
    └── InventoryService.get_low_stock_items(10, category="Widgets")
            │
            ▼
        UI updates with filtered data
```

### 5.3 Import Sequence (from UI)

```
User selects file + data type → clicks "Import"
    │
    ▼
ImportView._run_import(file_path, data_type)
    │
    ├── CSVImporter(data_type).import_file(file_path)
    │   └── Returns ImportResult
    │
    ├── Show result dialog (records imported, errors)
    │
    └── Trigger DashboardView.refresh() to update KPIs
```

---

## 6. KPI Calculation Details

### 6.1 Stock Health KPIs

**Days of Supply (per product):**
```
avg_daily_demand = SUM(quantity_sold) / COUNT(DISTINCT date)
                   WHERE date >= (today - lookback_days)
                   AND product_id = ?

days_of_supply = current_quantity / avg_daily_demand
                 (returns ∞ if avg_daily_demand = 0)
```

**Days of Supply (global):**
```
Weighted average across all products, weighted by inventory value.
```

**Inventory Turnover (period):**
```
cogs_sold = SUM(quantity_sold * unit_cost)
            WHERE date >= (today - lookback_days)

avg_inventory_value = (beginning_value + ending_value) / 2

turnover = cogs_sold / avg_inventory_value
```

### 6.2 Service Level KPIs

**Stockout Rate:**
```
stockout_count = COUNT(DISTINCT product_id)
                 WHERE product_id NOT IN (
                     SELECT product_id FROM inventory_levels WHERE quantity > 0
                 )

stockout_rate = stockout_count / total_products * 100
```

**Fill Rate (approximation from available data):**
```
Based on the ratio of products with stock vs. total products.
fill_rate = (products_with_stock / total_products) * 100

Note: True fill rate requires order-level data (Phase 5 enhancement).
```

### 6.3 Financial KPIs

**Total Inventory Value:**
```
SUM(inventory_levels.quantity * products.unit_cost)
```

**Estimated Carrying Cost:**
```
total_inventory_value * CARRYING_COST_RATE / 12   (monthly)
total_inventory_value * CARRYING_COST_RATE         (annual)
```

**Potential Margin:**
```
SUM(inventory_levels.quantity * (products.unit_price - products.unit_cost))
```

---

## 7. Technology Stack (Phase 2 Additions)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Desktop UI | customtkinter | >= 5.2.0 | Modern Tkinter widgets |
| Charts | matplotlib | >= 3.7.0 | Embedded chart rendering |
| Number formatting | babel | >= 2.12.0 | Currency and number locale formatting |

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

# Testing
pytest>=8.0.0
pytest-cov>=4.0.0

# Development (optional)
black>=23.0.0
isort>=5.12.0
mypy>=1.0.0
```

---

## 8. Implementation Tasks

### 8.1 Service Layer (Priority: High)

| # | Task | Module | Estimated Effort |
|---|------|--------|-----------------|
| 1 | Create `src/services/` package structure | `src/services/__init__.py` | 15 min |
| 2 | Implement InventoryService (queries + aggregations) | `src/services/inventory_service.py` | 3-4 hours |
| 3 | Implement SalesService (queries + period aggregations) | `src/services/sales_service.py` | 2-3 hours |
| 4 | Implement KPIService (all KPI calculations) | `src/services/kpi_service.py` | 4-5 hours |
| 5 | Add KPI constants to configuration | `config/constants.py` | 30 min |
| 6 | Write service layer unit tests | `tests/test_services.py` | 3-4 hours |
| 7 | Write KPI calculation tests with known data | `tests/test_kpi.py` | 3-4 hours |

### 8.2 UI Foundation (Priority: High)

| # | Task | Module | Estimated Effort |
|---|------|--------|-----------------|
| 8 | Install Phase 2 dependencies | `requirements.txt` | 15 min |
| 9 | Create `src/ui/` package structure | `src/ui/__init__.py` | 15 min |
| 10 | Define theme constants and color palette | `src/ui/theme.py` | 1 hour |
| 11 | Implement main application window + navigation | `src/ui/app.py` | 3-4 hours |
| 12 | Create application entry point | `main.py` | 30 min |
| 13 | Add UI settings to configuration | `config/settings.py` | 30 min |

### 8.3 Reusable Components (Priority: High)

| # | Task | Module | Estimated Effort |
|---|------|--------|-----------------|
| 14 | Implement KPI card widget | `src/ui/components/kpi_card.py` | 2 hours |
| 15 | Implement data table widget (sortable, selectable) | `src/ui/components/data_table.py` | 4-5 hours |
| 16 | Implement chart panel (Matplotlib embed) | `src/ui/components/chart_panel.py` | 3-4 hours |
| 17 | Implement filter bar (dropdowns, search, refresh) | `src/ui/components/filter_bar.py` | 2-3 hours |
| 18 | Implement status bar | `src/ui/components/status_bar.py` | 1 hour |
| 19 | Implement import dialog | `src/ui/components/import_dialog.py` | 2-3 hours |

### 8.4 Views (Priority: High)

| # | Task | Module | Estimated Effort |
|---|------|--------|-----------------|
| 20 | Implement Dashboard view (KPIs + charts + alerts) | `src/ui/views/dashboard_view.py` | 5-6 hours |
| 21 | Implement Inventory view (table + detail panel) | `src/ui/views/inventory_view.py` | 4-5 hours |
| 22 | Implement Import view (file picker + history) | `src/ui/views/import_view.py` | 3-4 hours |

### 8.5 Integration & Testing (Priority: Medium)

| # | Task | Module | Estimated Effort |
|---|------|--------|-----------------|
| 23 | Write UI component tests (non-visual logic) | `tests/test_ui.py` | 2-3 hours |
| 24 | Create sample dataset for demo/testing | `data/imports/` | 1-2 hours |
| 25 | End-to-end testing (import → dashboard) | Manual | 2-3 hours |
| 26 | Performance testing with 10,000+ SKUs | Manual | 1-2 hours |

**Total estimated effort: ~55-70 hours**

---

## 9. Implementation Order

The recommended build sequence ensures each step can be tested before moving to the next:

```
Step 1: Service Layer
  ├── Task 1: Package structure
  ├── Task 5: KPI constants
  ├── Task 2: InventoryService
  ├── Task 3: SalesService
  ├── Task 4: KPIService
  ├── Task 6: Service tests
  └── Task 7: KPI tests
         │
Step 2: UI Foundation
  ├── Task 8:  Dependencies
  ├── Task 9:  Package structure
  ├── Task 10: Theme
  ├── Task 13: UI settings
  ├── Task 11: Main app window
  └── Task 12: Entry point
         │
Step 3: Components
  ├── Task 14: KPI card
  ├── Task 15: Data table
  ├── Task 16: Chart panel
  ├── Task 17: Filter bar
  ├── Task 18: Status bar
  └── Task 19: Import dialog
         │
Step 4: Views
  ├── Task 20: Dashboard view
  ├── Task 21: Inventory view
  └── Task 22: Import view
         │
Step 5: Integration
  ├── Task 23: UI tests
  ├── Task 24: Sample dataset
  ├── Task 25: E2E testing
  └── Task 26: Performance testing
```

---

## 10. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| CustomTkinter Treeview performance with 10K+ rows | High | Medium | Implement virtual scrolling / pagination; load visible rows only |
| Matplotlib rendering blocks UI thread | Medium | High | Render charts in separate thread or use `after()` scheduling |
| KPI calculations slow on large datasets | Medium | Medium | Use SQL-level aggregation (`func.sum`, `func.count`) instead of Python loops |
| Chart style inconsistency across OS | Low | Medium | Lock Matplotlib backend to TkAgg; use explicit font/color settings |
| Cross-platform layout issues | Medium | Medium | Use relative sizing and grid weights; test on macOS, Windows, Linux |
| Empty database crashes dashboard | High | High | Guard all services with null/empty checks; show "No data" state |

---

## 11. Testing Strategy

### 11.1 Service Layer Tests (`tests/test_services.py`)

Test with known data fixtures to verify exact calculation results:

| Test Area | Example Tests |
|-----------|---------------|
| InventoryService | Products returned with correct joined data; zero-stock filter works |
| SalesService | Period filter returns correct records; daily aggregation sums correctly |
| KPIService | Days of supply = stock / demand; turnover ratio matches expected |
| Edge Cases | Empty database returns zeros/defaults; single product; single day of sales |

### 11.2 KPI Tests (`tests/test_kpi.py`)

Dedicated tests with controlled data for arithmetic verification:

```python
# Example: 100 units in stock, 10 sold per day → 10 days of supply
def test_days_of_supply():
    # Insert 100 units for SKU001
    # Insert 10 sales per day for 7 days
    kpi = kpi_service.get_product_kpis("SKU001")
    assert kpi["days_of_supply"] == pytest.approx(10.0, rel=0.1)
```

### 11.3 UI Tests (`tests/test_ui.py`)

Test non-visual component logic without launching the window:

| Test Area | Example Tests |
|-----------|---------------|
| KPI Card | Value formatting (1234 → "1,234"), color selection by threshold |
| Data Table | Sort logic, filter matching, row highlighting rules |
| Filter Bar | Dropdown population from service data, callback invocation |
| Theme | Color constants are valid hex, font tuples are valid |

---

## 12. Non-Functional Requirements (Phase 2)

| Requirement | Target | Validation Method |
|-------------|--------|-------------------|
| Dashboard load time | < 2 seconds with 10K SKUs | Profiling with sample dataset |
| Table scroll performance | 60 FPS with 10K rows visible | Manual testing, pagination fallback |
| Chart render time | < 1 second per chart | Matplotlib render timing |
| Memory usage | < 200 MB with 10K SKUs loaded | Process monitoring |
| Window responsiveness | No freeze during data load | Threaded queries or `after()` callbacks |
| Cross-platform UI | Functional on macOS, Windows, Linux | Manual testing on each OS |

---

## 13. Phase 2 Exit Criteria

- [ ] Application launches with main window and navigation sidebar
- [ ] Dashboard view displays 6+ KPI cards with live data
- [ ] KPIs compute correctly (verified by unit tests with known data)
- [ ] Stock level table shows all products with sorting and filtering
- [ ] At least 2 chart types render correctly (bar + line)
- [ ] Filter bar filters data across KPIs, charts, and tables
- [ ] Import dialog triggers CSV/Excel import and refreshes dashboard
- [ ] Import history table shows past imports from `import_logs`
- [ ] Product detail panel shows per-warehouse stock breakdown on row click
- [ ] Status bar shows database connection and record counts
- [ ] Empty database shows "No data" state without errors
- [ ] Dashboard loads in < 2 seconds with 1,000 products
- [ ] All service layer tests pass
- [ ] All KPI calculation tests pass

---

## 14. Transition to Phase 3

Phase 3 (Analytics Engine) will build on the dashboard by:

1. **ABC Classification** -- categorize products by revenue contribution (A/B/C tiers)
2. **XYZ Classification** -- categorize by demand variability (coefficient of variation)
3. **Turnover Analysis** -- detailed turnover calculations by category, warehouse, period
4. **Analytics integration** -- display classification results on the dashboard (badges, color coding)

**Prerequisites from Phase 2:**
- Working service layer for querying inventory and sales data
- Dashboard UI framework for displaying analytics results
- Chart panel for visualizing classification distributions
- Data table capable of showing additional computed columns

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-19 | Initial Phase 2 implementation plan |

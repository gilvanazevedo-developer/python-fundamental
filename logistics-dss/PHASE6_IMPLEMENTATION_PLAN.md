# Logistics DSS - Phase 6 Implementation Plan
# Executive Dashboard & Reporting

**Project:** Logistics Decision Support System
**Phase:** 6 of 8 - Executive Dashboard & Reporting
**Author:** Gilvan de Azevedo
**Date:** 2026-02-20
**Status:** Not Started
**Depends on:** Phase 5 (Inventory Optimization) -- functionally complete

---

## 1. Phase 6 Objective

Build an executive-grade reporting layer that surfaces the system's accumulated analytical intelligence — Phase 3 ABC-XYZ classifications, Phase 4 demand forecasts, and Phase 5 inventory policies — in consolidated, export-ready views suited for management review. Phase 6 delivers two new screens (Executive Dashboard and Report Generator), a full-featured PDF and Excel export engine, and cross-run trend analysis showing how optimization quality evolves over time.

The system transitions from an operational tool (used by stock controllers and buyers) into a strategic reporting platform: senior managers can open a single Executive Dashboard view, grasp the portfolio's health across eight headline KPIs, drill into ABC cost distribution and stockout risk, and export a PDF executive summary for the next board meeting — all without navigating through the underlying data screens.

**Deliverables:**
- Executive Dashboard View: 4-section screen with headline KPIs, cost trend chart, ABC distribution, and top-5 stockout risk panel
- Reports View: report type selector, parameter controls, generation history table, one-click export
- PDF export engine (ReportLab) covering four report types: Inventory Policy, Forecast Accuracy, Alert History, Executive Summary
- Excel export engine (openpyxl) for the same four report types, with multi-sheet workbooks and auto-fitted columns
- `ReportRunner` orchestrator dispatching to the correct exporter by type and format
- `ReportService` query layer aggregating executive KPIs, run histories, and comparison deltas
- `OptimizationService.compare_runs()` — per-product and portfolio-level delta between two optimization runs
- `OptimizationService.get_run_history()` — ordered list of all optimization runs for trend display
- `ReportLog` ORM model auditing every report generation event
- Full test suite (40 new tests) covering all exporter methods, report runner dispatch, service layer, and executive KPI computation

---

## 2. Phase 5 Dependencies (Available)

Phase 6 builds directly on the following Phase 5 components:

| Component | Module | Usage in Phase 6 |
|-----------|--------|-------------------|
| OptimizationRun model | `src/database/models.py` | Run history; compare_runs() source; headline run timestamp |
| InventoryPolicy model | `src/database/models.py` | Per-product policy data for Inventory Policy Report and Executive KPI cards |
| ReplenishmentAlert model | `src/database/models.py` | Alert History Report; active alert counts for Executive Dashboard |
| OptimizationService | `src/services/optimization_service.py` | Extended with compare_runs(), get_run_history(); get_cost_summary() powers Executive KPI |
| KPIService | `src/services/kpi_service.py` | Extended with get_executive_kpis() aggregating all phases |
| ForecastRun model | `src/database/models.py` | Forecast Accuracy Report source; run timestamp trend |
| DemandForecast model | `src/database/models.py` | Per-product MAPE, MAE, RMSE for Forecast Accuracy Report |
| ForecastService | `src/services/forecast_service.py` | get_accuracy_table() for Forecast Accuracy Report |
| ProductClassification model | `src/database/models.py` | ABC-XYZ distribution pie chart in Executive Dashboard |
| AnalyticsService | `src/services/analytics_service.py` | Revenue share by ABC class for Executive KPI |
| InventoryService | `src/services/inventory_service.py` | Current stock levels for top-5 risk table |
| AlertsView | `src/ui/views/alerts_view.py` | Executive Dashboard "View All Alerts" link target |
| OptimizationView | `src/ui/views/optimization_view.py` | Executive Dashboard "View Policies" link target |
| ChartPanel | `src/ui/components/chart_panel.py` | Extended with plot_cost_trend(), plot_alert_history() |
| KPICard | `src/ui/components/kpi_card.py` | Extended with trend delta indicator (▲/▼ vs. prior run) |
| DataTable | `src/ui/components/data_table.py` | Top-5 risk table and report history table |
| DatabaseManager | `src/database/connection.py` | Sessions for ReportLog persistence |
| LoggerMixin | `src/logger.py` | Logging across all new reporting modules |
| Constants | `config/constants.py` | Extended with report format, PDF layout, and export constants |

---

## 3. Architecture Overview

### 3.1 Phase 6 Directory Structure

```
logistics-dss/
├── config/
│   ├── settings.py                 # (existing)
│   └── constants.py                # + report format, PDF layout, executive KPI constants
├── src/
│   ├── reporting/                  # NEW: Report Generation Engine
│   │   ├── __init__.py
│   │   ├── base_report.py              # Abstract base: data-gathering interface + report metadata
│   │   ├── pdf_exporter.py             # ReportLab PDF: header, tables, charts, footer
│   │   ├── excel_exporter.py           # openpyxl Excel: multi-sheet workbook, auto-fitted columns
│   │   └── report_runner.py            # Orchestrator: resolves type → exporter → ReportLog
│   ├── services/
│   │   ├── report_service.py           # NEW: executive KPI aggregation + report log queries
│   │   ├── optimization_service.py     # (existing) + compare_runs() + get_run_history()
│   │   ├── kpi_service.py              # (existing) + get_executive_kpis()
│   │   ├── inventory_service.py        # (existing)
│   │   ├── sales_service.py            # (existing)
│   │   ├── analytics_service.py        # (existing)
│   │   └── forecast_service.py         # (existing)
│   ├── database/
│   │   ├── connection.py               # (existing)
│   │   └── models.py                   # + ReportLog ORM model
│   └── ui/
│       ├── app.py                      # + Executive + Reports nav buttons
│       ├── theme.py                    # + executive dashboard color constants
│       ├── components/
│       │   ├── chart_panel.py          # + plot_cost_trend() + plot_alert_history()
│       │   └── kpi_card.py             # + trend delta indicator (▲/▼ % vs. prior run)
│       └── views/
│           ├── executive_view.py       # NEW: Executive Summary screen (4 sections)
│           ├── reports_view.py         # NEW: Report Generator screen (3 sections)
│           ├── dashboard_view.py       # (existing) + "Executive Summary →" shortcut link
│           ├── optimization_view.py    # (existing)
│           └── alerts_view.py          # (existing)
├── tests/
│   ├── test_pdf_exporter.py            # NEW: PDF generation content and structure tests
│   ├── test_excel_exporter.py          # NEW: Excel workbook structure and cell value tests
│   ├── test_report_runner.py           # NEW: dispatch + ReportLog persistence tests
│   ├── test_report_service.py          # NEW: executive KPI and report log query tests
│   ├── test_executive_kpis.py          # NEW: headline KPI computation tests
│   └── test_optimization_compare.py    # NEW: compare_runs() delta and get_run_history() tests
└── main.py                             # (existing)
```

### 3.2 Layer Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          Presentation Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │Dashboard │  │ Forecast │  │Optimiz.  │  │ Alerts   │  │ Executive  │ │
│  │ View (+) │  │  View    │  │ View     │  │ View     │  │ View (NEW) │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │        Reusable Components (+ extensions)                            │ │
│  │  KPICard(+) | DataTable | ChartPanel(+) | Badge | Reports View (NEW)│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────────── ┤
│                           Service Layer                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐   │
│  │ Optimization│  │  Forecast   │  │  Analytics  │  │    Report     │   │
│  │ Service (+) │  │  Service    │  │  Service    │  │ Service (NEW) │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────┬───────┘   │
├────────────────────────────────────────────────────────────┼────────────┤
│                    Reporting Engine (NEW)                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       ReportRunner                              │   │
│  │   ┌───────────────┐   ┌──────────────┐   ┌──────────────────┐  │   │
│  │   │  BaseReport   │   │ PDFExporter  │   │  ExcelExporter   │  │   │
│  │   │  (abstract)   │   │  (ReportLab) │   │  (openpyxl)      │  │   │
│  │   └───────────────┘   └──────────────┘   └──────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├───────────────────────────────────────────────────────────────────────  ┤
│          Optimization Engine (Phase 5) + Forecasting Engine (Phase 4)    │
│  ┌──────────────────┐  ┌──────────────────────────────────────────────┐ │
│  │  OptimizationRun │  │  ORM Models                                  │ │
│  │  InventoryPolicy │  │  (+ ReportLog)                               │ │
│  │  ReplenishAlert  │  │                                              │ │
│  └──────────────────┘  └──────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Database Model: ReportLog

Audit trail for every report generation event:

```python
class ReportLog(Base):
    __tablename__ = "report_logs"

    id                  = Column(Integer,  primary_key=True)
    generated_at        = Column(DateTime, default=func.now())

    report_type         = Column(String(20), nullable=False)
    # Values: "POLICY" | "FORECAST" | "ALERT" | "EXECUTIVE"

    export_format       = Column(String(10), nullable=False)
    # Values: "PDF" | "EXCEL"

    file_path           = Column(String(500), nullable=True)   # absolute path on disk; None if in-memory
    file_size_bytes     = Column(Integer,    nullable=True)

    optimization_run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=True)
    forecast_run_id     = Column(Integer, ForeignKey("forecast_runs.id"),     nullable=True)

    generated_by        = Column(String(100), nullable=True)   # user label / session tag
    generation_seconds  = Column(Float,    nullable=False)

    success             = Column(Boolean,  nullable=False, default=True)
    error_message       = Column(Text,     nullable=True)   # set on failure; success=False
```

**Indexes:**
- `(report_type, generated_at DESC)` — report type history
- `(generated_at DESC)` — chronological report log (shown in ReportsView history table)
- `(success, generated_at DESC)` — filter failed generations for diagnostics

---

### 4.2 Reporting Engine

#### 4.2.1 Base Report (`src/reporting/base_report.py`)

Abstract base defining the data-gathering interface and shared metadata:

```python
@dataclass
class ReportMetadata:
    report_type:         str               # "POLICY" | "FORECAST" | "ALERT" | "EXECUTIVE"
    export_format:       str               # "PDF" | "EXCEL"
    title:               str               # human-readable report title
    generated_at:        datetime
    generated_by:        Optional[str]
    optimization_run_id: Optional[int]
    forecast_run_id:     Optional[int]
    page_count:          Optional[int]     # PDF only; None for Excel
    sheet_names:         List[str]         # Excel only; empty for PDF
```

```python
class BaseReport(ABC, LoggerMixin):

    @abstractmethod
    def gather_data(self, **kwargs) -> Dict[str, Any]:
        """Query all data required for the report; returns structured dict."""

    @abstractmethod
    def render(self, data: Dict[str, Any], output_path: str) -> ReportMetadata:
        """Write the report to output_path; return populated metadata."""

    def _format_currency(self, value: Optional[float]) -> str:
        """Format float as '$1,234.56'; returns '—' for None."""

    def _format_percentage(self, value: Optional[float], decimals: int = 1) -> str:
        """Format float as '11.9%'; returns '—' for None."""

    def _format_date(self, dt: Optional[datetime]) -> str:
        """Format datetime using REPORT_DATE_FORMAT constant; returns '—' for None."""
```

---

#### 4.2.2 PDF Exporter (`src/reporting/pdf_exporter.py`)

Uses **ReportLab** (`reportlab>=4.0`) to generate styled, multi-section PDF reports.

**Supported report types and their PDF layouts:**

| Report Type | Sections |
|-------------|---------|
| `POLICY` | Cover page → Portfolio summary KPIs → Per-product policy table → ABC cost breakdown chart → Alert summary table |
| `FORECAST` | Cover page → Portfolio MAPE summary → Per-product accuracy table (ranked by MAPE) → Model usage bar chart → Adequacy assessment table |
| `ALERT` | Cover page → Active alerts by severity (with details) → Alert history summary → Acknowledged alerts with resolution notes |
| `EXECUTIVE` | Single-page: headline KPIs (8 cards) → ABC cost pie chart → Portfolio risk matrix → Top-5 stockout products |

**PDF styling constants used from `config/constants.py`:**

| Constant | Value | Purpose |
|----------|-------|---------|
| `PDF_PAGE_SIZE` | `"A4"` | Page dimensions (210 × 297 mm) |
| `PDF_MARGIN_MM` | `20` | Page margin on all sides |
| `PDF_FONT_TITLE` | `"Helvetica-Bold"` | Section headings |
| `PDF_FONT_BODY` | `"Helvetica"` | Table cells and body text |
| `PDF_FONT_SIZE_TITLE` | `16` | Cover title font size |
| `PDF_FONT_SIZE_HEADING` | `12` | Section heading font size |
| `PDF_FONT_SIZE_BODY` | `9` | Table body font size |
| `PDF_TABLE_HEADER_COLOR` | `"#1f6aa5"` | Table header background (blue) |
| `PDF_TABLE_ROW_ALT_COLOR` | `"#f0f4f8"` | Alternating row background (light blue-grey) |

**Class `PDFExporter(BaseReport)`:**

| Method | Description |
|--------|-------------|
| `gather_data(report_type, opt_run_id, fc_run_id) -> Dict` | Queries DB via service layer; returns type-specific data dict |
| `render(data, output_path) -> ReportMetadata` | Builds PDF document; writes to `output_path`; returns metadata with `page_count` |
| `_build_cover_page(canvas, data)` | Title, subtitle, date, logo placeholder |
| `_build_kpi_table(canvas, kpis)` | 2×4 grid of KPI cards with value + label |
| `_build_product_table(canvas, rows, columns)` | Paginated table with header repeat and alternating row colours |
| `_build_chart(canvas, chart_type, data)` | Embeds matplotlib figure as PNG via ReportLab's `Image` element |
| `_build_footer(canvas, page_num, total_pages)` | Page X of Y, generated timestamp, company placeholder |

**Inline matplotlib charts in PDF:**
```python
# PDF charts: render matplotlib figure to BytesIO PNG → ReportLab Image
import io
from reportlab.platypus import Image as RLImage

def _build_chart(self, fig: plt.Figure) -> RLImage:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return RLImage(buf, width=400, height=250)
```

---

#### 4.2.3 Excel Exporter (`src/reporting/excel_exporter.py`)

Uses **openpyxl** (already in the Python environment via pandas Excel support) to generate multi-sheet `.xlsx` workbooks.

**Supported report types and their sheet layouts:**

| Report Type | Sheets |
|-------------|--------|
| `POLICY` | `Summary` (portfolio KPIs) + `Policies` (per-product table) + `Costs` (ABC class breakdown) + `Alerts` (active alerts) |
| `FORECAST` | `Summary` (MAPE overview) + `Accuracy` (per-product table) + `Adequacy` (stock coverage table) |
| `ALERT` | `Active` (unacknowledged alerts) + `History` (all alerts with acknowledged status) |
| `EXECUTIVE` | `Executive` (single consolidated sheet with all headline metrics) |

**Class `ExcelExporter(BaseReport)`:**

| Method | Description |
|--------|-------------|
| `gather_data(report_type, opt_run_id, fc_run_id) -> Dict` | Same data gathering as PDFExporter (delegates to ReportService) |
| `render(data, output_path) -> ReportMetadata` | Creates `openpyxl.Workbook`; writes one sheet per section; applies styles; saves |
| `_write_sheet(ws, headers, rows, header_style)` | Writes header row + data rows; applies alternating fill to data rows |
| `_auto_fit_columns(ws)` | Sets `column_dimensions[col].width` to max(header_len, max_value_len) + 2 |
| `_apply_header_style(ws, header_row)` | Blue fill + white bold font for header cells |
| `_apply_conditional_formatting(ws, col_idx, thresholds)` | Red/amber/green fill for MAPE, severity, and alert type columns |
| `_add_summary_chart(ws, chart_type, data_range)` | Embeds openpyxl `BarChart`/`PieChart` in the Summary sheet |

**Excel styling applied:**

| Element | Style |
|---------|-------|
| Header row | `#1f6aa5` fill, white bold font, 11pt |
| Alternating data rows | `#f0f4f8` and `#ffffff` |
| CRITICAL cells | `#d64545` fill (red) |
| HIGH cells | `#e8a838` fill (amber) |
| MAPE > 20% | `#d64545` fill (poor accuracy) |
| MAPE ≤ 10% | `#2fa572` fill (excellent accuracy) |
| Currency cells | `$#,##0.00` number format |
| Percentage cells | `0.0%` number format |

---

#### 4.2.4 Report Runner (`src/reporting/report_runner.py`)

Orchestrates report generation: resolves type → exporter, runs data gathering + rendering, persists a `ReportLog` row.

**Class `ReportRunner`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `generate(report_type, export_format, output_path, opt_run_id, fc_run_id, generated_by) -> ReportLog` | Persisted log row | Full pipeline: validate params → instantiate exporter → gather_data → render → persist ReportLog |
| `get_supported_types() -> List[str]` | `["POLICY", "FORECAST", "ALERT", "EXECUTIVE"]` | Validation list for UI dropdowns |
| `get_supported_formats(report_type) -> List[str]` | e.g. `["PDF", "EXCEL"]` | EXECUTIVE only supports PDF; others support both |
| `get_default_filename(report_type, export_format) -> str` | e.g. `"policy_report_20260220.pdf"` | Suggested filename for file dialog |

**Dispatch table:**
```python
_EXPORTER_MAP = {
    "PDF":   PDFExporter,
    "EXCEL": ExcelExporter,
}

_FORMAT_CONSTRAINTS = {
    "EXECUTIVE": ["PDF"],          # single-page layout not suitable for multi-sheet Excel
    "POLICY":    ["PDF", "EXCEL"],
    "FORECAST":  ["PDF", "EXCEL"],
    "ALERT":     ["PDF", "EXCEL"],
}
```

**`generate()` flow:**
```
1. Validate report_type and export_format (raises ValueError on invalid combination)
2. Resolve output_path (if None: use REPORT_DEFAULT_EXPORT_DIR / default_filename)
3. Instantiate exporter = _EXPORTER_MAP[export_format]()
4. t_start = time.monotonic()
5. data = exporter.gather_data(report_type, opt_run_id, fc_run_id)
6. metadata = exporter.render(data, output_path)
7. duration = time.monotonic() - t_start
8. file_size = os.path.getsize(output_path)
9. log = ReportLog(report_type=..., export_format=..., file_path=output_path,
                  file_size_bytes=file_size, generation_seconds=duration,
                  success=True, ...)
10. session.add(log); session.commit()
11. Return log

On exception:
    log = ReportLog(..., success=False, error_message=str(e))
    session.add(log); session.commit()
    raise
```

---

### 4.3 Report Service (`src/services/report_service.py`)

Central query layer for all executive-grade aggregations and report log queries:

| Method | Returns | Description |
|--------|---------|-------------|
| `get_executive_kpis() -> Dict` | 8-metric executive summary | Combines KPIs from all phases (see §6.2) |
| `get_report_log(limit) -> List[Dict]` | Last N report generations | Ordered by `generated_at DESC`; includes success status and file size |
| `get_run_history() -> List[Dict]` | All optimization + forecast runs | Ordered by timestamp DESC; joined for comparative display |
| `get_top_risk_products(n) -> List[Dict]` | Top N stockout-risk products | Ordered by `days_until_stockout ASC` (None last); includes current stock, ROP, alert severity |
| `get_abc_distribution() -> Dict` | `{"A": 8, "B": 6, "C": 6}` and revenue shares | Used in Executive Dashboard ABC pie chart |
| `get_cost_trend(last_n_runs) -> List[Dict]` | Per-run `total_annual_cost` | Ordered by `run_timestamp ASC`; used in cost trend line chart |
| `get_alert_history_summary(weeks) -> List[Dict]` | Per-week alert counts by severity | For alert history bar chart in Executive Dashboard |

---

### 4.4 OptimizationService Extensions (`src/services/optimization_service.py`)

#### 4.4.1 `compare_runs(run_id_1, run_id_2) -> Dict`

Computes per-product and portfolio-level deltas between two optimization runs:

```python
def compare_runs(self, run_id_1: int, run_id_2: int) -> Dict:
    """
    Returns:
        {
            "run_1": OptimizationRun dict (earlier),
            "run_2": OptimizationRun dict (later),
            "portfolio_delta": {
                "total_annual_cost_delta":  float,   # run_2 - run_1
                "total_annual_cost_pct":    float,   # % change
                "avg_safety_stock_delta":   float,   # avg SS change across products
                "avg_eoq_delta":            float,
                "alerts_delta":             int,     # run_2.alerts_generated - run_1.alerts_generated
            },
            "product_deltas": [
                {
                    "product_id": int,
                    "sku_code": str,
                    "product_name": str,
                    "abc_class": str,
                    "ss_before":    float, "ss_after":    float, "ss_delta":    float,
                    "eoq_before":   float, "eoq_after":   float, "eoq_delta":   float,
                    "rop_before":   float, "rop_after":   float, "rop_delta":   float,
                    "cost_before":  float, "cost_after":  float, "cost_delta":  float,
                    "cost_pct":     float,
                },
                ...
            ]
        }
    """
```

**Typical use case:** After running Phase 4 a second time (with more historical data, improving MAPE from 11.9% → 9.5%), run Phase 5 optimization again. `compare_runs(run_id=1, run_id=2)` shows that lower RMSE reduced safety stocks by an average 18%, cutting annual holding cost by $4,200.

#### 4.4.2 `get_run_history() -> List[Dict]`

Returns all optimization runs ordered by `run_timestamp DESC`:
```python
[
    {
        "run_id":              int,
        "run_timestamp":       datetime,
        "total_products":      int,
        "policies_generated":  int,
        "alerts_generated":    int,
        "total_annual_cost":   float,
        "run_duration_seconds":float,
        "forecast_run_id":     Optional[int],
    },
    ...
]
```

Used in ExecutiveView cost trend chart (x-axis = run index / date, y-axis = `total_annual_cost`).

---

### 4.5 KPI Service Extension (`src/services/kpi_service.py`)

#### 4.5.1 `get_executive_kpis() -> Dict`

Returns all 8 headline KPIs for the Executive Dashboard's top card row:

| KPI Key | Source | Description |
|---------|--------|-------------|
| `total_products` | `COUNT(products)` | Total active products in portfolio |
| `portfolio_annual_cost` | Latest `OptimizationRun.total_annual_cost` | Annual holding + ordering cost ($) |
| `portfolio_mape` | Latest `ForecastRun.portfolio_mape` | Revenue-weighted forecast MAPE (%) |
| `active_critical_alerts` | `COUNT(replenishment_alerts WHERE severity=CRITICAL AND is_acknowledged=False)` | Unacknowledged critical alerts |
| `a_class_cost_share` | A-class cost / total portfolio cost | Share of annual cost from A-class products (%) |
| `excess_product_count` | Products with `alert_type=EXCESS` in latest run | Products overstocked beyond max_stock |
| `stockout_product_count` | Products with `alert_type=STOCKOUT` in latest run (unacknowledged) | Products with stock=0 |
| `last_optimization_at` | Latest `OptimizationRun.run_timestamp` | ISO timestamp of most recent full optimization run |

**Trend indicators (delta vs. prior run):**
Each KPI additionally returns `*_delta` and `*_direction` ("up" / "down" / "stable") computed against the previous `OptimizationRun`. The `KPICard` component renders these as a small `▲ +2.4%` or `▼ −$3,100` annotation beneath the main value.

---

### 4.6 Presentation Layer

#### 4.6.1 Theme Extensions (`src/ui/theme.py`)

New executive dashboard color constants:

| Constant | Value | Usage |
|----------|-------|-------|
| `COLOR_EXEC_POSITIVE` | `"#2fa572"` | Positive trend delta (cost down, MAPE down) |
| `COLOR_EXEC_NEGATIVE` | `"#d64545"` | Negative trend delta (cost up, alerts up) |
| `COLOR_EXEC_NEUTRAL` | `"#6b7280"` | No change delta (stable) |
| `COLOR_EXEC_BACKGROUND` | `"#0f1724"` | Executive Dashboard section background (dark navy) |
| `COLOR_TREND_LINE` | `"#1f6aa5"` | Cost trend line chart color (blue) |
| `COLOR_ABC_A` | `"#d64545"` | ABC pie chart: A-class segment (red) |
| `COLOR_ABC_B` | `"#e8a838"` | ABC pie chart: B-class segment (amber) |
| `COLOR_ABC_C` | `"#2fa572"` | ABC pie chart: C-class segment (green) |

---

#### 4.6.2 ChartPanel Extension (`src/ui/components/chart_panel.py`)

Two new methods:

```python
def plot_cost_trend(self, run_timestamps: List[datetime],
                   total_costs: List[float], title: str) -> None:
    """
    Line chart: x-axis = optimization run date, y-axis = total_annual_cost ($).
    Reference line at current value. Marker at each run point.
    Used in ExecutiveView cost trend section.
    """

def plot_alert_history(self, weeks: List[str],
                      critical: List[int], high: List[int],
                      medium: List[int], low: List[int],
                      title: str) -> None:
    """
    Stacked bar chart: x-axis = calendar weeks, y-axis = alert count.
    Stack colors: CRITICAL=red, HIGH=amber, MEDIUM=blue, LOW=gray.
    Used in ExecutiveView recent alerts summary section.
    """
```

---

#### 4.6.3 KPICard Extension (`src/ui/components/kpi_card.py`)

New optional `delta` parameter renders a trend indicator beneath the main KPI value:

```python
class KPICard(CTkFrame):
    def update(self, value: str, subtitle: str = "",
               color: str = ...,
               delta: Optional[str] = None,
               delta_direction: Optional[str] = None) -> None:
        """
        delta: e.g. "▲ +$1,200" or "▼ −3.1%"
        delta_direction: "up" | "down" | "stable"
            → "up" with positive context (MAPE down = good): COLOR_EXEC_POSITIVE
            → "up" with negative context (cost up = bad): COLOR_EXEC_NEGATIVE
            → "stable": COLOR_EXEC_NEUTRAL
        """
```

---

#### 4.6.4 Executive View (`src/ui/views/executive_view.py`)

New dedicated executive summary screen:

```
┌──────────────────────────────────────────────────────────────────────┐
│  EXECUTIVE SUMMARY — 2026-02-20 18:55                                │
│  Last Optimization: 3.2s  |  Last Forecast: 23.4s                   │
├──────────────────────────────────────────────────────────────────────┤
│  HEADLINE KPIs (8 cards × 2 rows)                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │20 Prods  │ │ $33,442  │ │  11.9%  │ │  1 CRIT  │               │
│  │ Managed  │ │Ann. Cost │ │   MAPE  │ │  Alerts  │               │
│  │          │ │▼ −$1,200 │ │▼ −0.3%  │ │          │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ 8 A-Class│ │  72.7%  │ │  18 XCES │ │  1 OOST  │               │
│  │ Products │ │ A-Class  │ │  Excess  │ │  Stockout│               │
│  │          │ │ Cost Shr │ │          │ │          │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
├──────────────────────────────────────────────────────────────────────┤
│  COST TREND (left 55%)           │  ABC DISTRIBUTION (right 45%)    │
│                                  │                                   │
│  $34K ┤ ●                        │        ██ A (8 / 40%)            │
│  $33K ┤   ●                      │   Pie  ██ B (6 / 30%)            │
│  $32K ┤     ●                    │  Chart ██ C (6 / 30%)            │
│       └────────────────          │                                   │
│       Run 1  Run 2  Run 3        │  Revenue: A=72.7%  B=21.0%       │
│                                  │           C=6.3%                  │
├──────────────────────────────────────────────────────────────────────┤
│  TOP-5 STOCKOUT RISK             │  RECENT ALERTS (4 weeks)          │
│  ┌──────┬──────────┬──┬───┬────┐ │  ┌──────────────────────────────┐│
│  │ SKU  │ Product  │AB│Stk│Days│ │  │ ■CRIT ■HIGH □MED □LOW        ││
│  ├──────┼──────────┼──┼───┼────┤ │  │ Wk4 ██████████████           ││
│  │SK010 │Gadget U. │A │  0│  0 │ │  │ Wk3 ████                     ││
│  │SK009 │Gadget L. │B │ 53│22.1│ │  │ Wk2 ██████                   ││
│  │SK008 │Gadget M. │A │490│31.0│ │  │ Wk1 ████                     ││
│  │SK011 │Power Drl │A │648│66.8│ │  └──────────────────────────────┘│
│  │SK012 │Elec. Saw │B │405│88.0│ │                                   │
│  └──────┴──────────┴──┴───┴────┘ │  [View All Alerts →]             │
└──────────────────────────────────────────────────────────────────────┘
                             [Export Executive Summary PDF]
```

**Four sections:**

1. **Header Bar:** Report title + run timestamps
2. **Headline KPI Cards:** 2×4 grid of `KPICard` widgets with delta indicators (▲/▼ vs. prior optimization run)
3. **Cost Trend Chart + ABC Distribution Pie** (side-by-side):
   - Left: `ChartPanel.plot_cost_trend()` — line chart of `total_annual_cost` per optimization run
   - Right: `ChartPanel` pie chart of ABC product and revenue distribution
4. **Top-5 Risk Table + Alert History Bar** (side-by-side):
   - Left: `DataTable` — top 5 products ordered by `days_until_stockout ASC`; click navigates to AlertsView for that product
   - Right: `ChartPanel.plot_alert_history()` — 4-week stacked bar chart of alert volumes by severity

**Bottom action bar:**
- `[Export Executive Summary PDF]` button: calls `ReportRunner.generate("EXECUTIVE", "PDF", ...)` inline; opens file save dialog
- `[Compare Runs]` button (shown only when ≥ 2 optimization runs exist): opens a modal dialog with the compare_runs delta table

---

#### 4.6.5 Reports View (`src/ui/views/reports_view.py`)

Dedicated screen for on-demand report generation with history:

```
┌──────────────────────────────────────────────────────────────────────┐
│  REPORT GENERATOR                                                     │
├──────────────────────────────────────────────────────────────────────┤
│  REPORT PARAMETERS                                                    │
│  Report Type: [Inventory Policy ▼]   Format: [PDF ▼]                │
│  Optimization Run: [Latest (2026-02-20 18:55) ▼]                    │
│  Forecast Run:     [Latest (2026-02-20 14:07) ▼]                    │
│  Output Path:      [/Users/gilvan/reports/______]  [Browse...]       │
│                                             [Generate Report]        │
├──────────────────────────────────────────────────────────────────────┤
│  GENERATION PROGRESS                                                  │
│  ████████████████████████████████████████  100%  Done in 4.1s       │
│  ✓ policy_report_20260220.pdf  (148 KB)   [Open File]  [Open Folder]│
├──────────────────────────────────────────────────────────────────────┤
│  REPORT HISTORY                                                       │
│  ┌──────────────────────┬──────────────┬──────┬──────┬────────────┐  │
│  │ Generated At         │ Report Type  │ Fmt  │  KB  │ Status     │  │
│  ├──────────────────────┼──────────────┼──────┼──────┼────────────┤  │
│  │ 2026-02-20 19:05:42  │ POLICY       │ PDF  │ 148  │ ✓ Success  │  │
│  │ 2026-02-20 19:03:11  │ EXECUTIVE    │ PDF  │  82  │ ✓ Success  │  │
│  │ 2026-02-20 19:01:38  │ FORECAST     │ XLSX │  94  │ ✓ Success  │  │
│  └──────────────────────┴──────────────┴──────┴──────┴────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Three sections:**

1. **Report Parameters:**
   - Report Type `CTkOptionMenu`: ["Inventory Policy", "Forecast Accuracy", "Alert History", "Executive Summary"]
   - Format `CTkOptionMenu`: ["PDF", "Excel"] — Excel option disabled for Executive Summary (PDF only)
   - Optimization Run selector: dropdown of all `OptimizationRun` entries (latest pre-selected)
   - Forecast Run selector: dropdown of all `ForecastRun` entries (latest pre-selected)
   - Output path: text field + "Browse..." button opens `filedialog.asksaveasfilename()`
   - "Generate Report" button: starts background thread

2. **Generation Progress:** Progress bar + status label; "Open File" and "Open Folder" links shown after completion

3. **Report History:** `DataTable` showing `ReportLog` rows (last 20); double-click row → opens file if it still exists on disk

**Background thread pattern:**
```python
def _generate_report(self):
    self._set_generating_state(True)
    thread = threading.Thread(target=self._generation_worker, daemon=True)
    thread.start()

def _generation_worker(self):
    try:
        log = self.report_runner.generate(
            report_type=self._get_report_type(),
            export_format=self._get_format(),
            output_path=self._output_path_var.get(),
            opt_run_id=self._get_opt_run_id(),
            fc_run_id=self._get_fc_run_id(),
        )
        self.after(0, lambda: self._on_generation_complete(log))
    except Exception as e:
        self.after(0, lambda: self._on_generation_error(str(e)))
```

---

#### 4.6.6 Dashboard View Extension (`src/ui/views/dashboard_view.py`)

New shortcut link added between the existing KPI cards and the critical alerts strip:

```
[Executive Summary →]   Quick-access banner; navigates to ExecutiveView
```

---

#### 4.6.7 App Navigation Extension (`src/ui/app.py`)

- Add **"Executive"** nav button (8th position, after Alerts)
- Add **"Reports"** nav button (9th position, after Executive)
- `ExecutiveView` and `ReportsView` instantiated lazily on first navigation click

---

## 5. Data Flow

### 5.1 Report Generation Sequence

```
User selects report type + format in ReportsView and clicks "Generate Report"
    │
    ▼
ReportsView._generation_worker()   (background thread)
    │
    ▼
ReportRunner.generate(report_type, export_format, output_path, ...)
    │
    ├── Validate: report_type ∈ SUPPORTED_TYPES
    │             export_format ∈ FORMAT_CONSTRAINTS[report_type]
    │             → raises ValueError if invalid
    │
    ├── exporter = PDFExporter() or ExcelExporter()
    │
    ├── data = exporter.gather_data(report_type, opt_run_id, fc_run_id)
    │       ├── ReportService.get_executive_kpis()   (for all types)
    │       ├── OptimizationService.get_latest_policies()  (for POLICY)
    │       ├── ForecastService.get_accuracy_table()       (for FORECAST)
    │       ├── OptimizationService.get_active_alerts()    (for ALERT)
    │       └── ReportService.get_top_risk_products()      (for EXECUTIVE)
    │
    ├── metadata = exporter.render(data, output_path)
    │       → Writes PDF or XLSX file to output_path
    │
    ├── file_size = os.path.getsize(output_path)
    │
    ├── log = ReportLog(..., success=True, file_size_bytes=file_size)
    │   session.add(log); session.commit()
    │
    └── return log
            │ (main thread via after())
            ▼
    ReportsView._on_generation_complete(log)
        ├── Update progress bar → 100%
        ├── Show "Open File" and "Open Folder" links
        └── Reload report history table
```

### 5.2 Executive Dashboard Load Sequence

```
User navigates to ExecutiveView (first click or tab switch)
    │
    ▼
ExecutiveView._load_data()   (background thread)
    │
    ├── ReportService.get_executive_kpis()           → 8 KPI dicts + deltas
    ├── ReportService.get_cost_trend(last_n_runs=6)  → run history for trend chart
    ├── ReportService.get_abc_distribution()          → product/revenue counts by class
    ├── ReportService.get_top_risk_products(n=5)      → top 5 stockout risk products
    └── ReportService.get_alert_history_summary(weeks=4) → weekly alert counts
            │ (main thread via after())
            ▼
    ExecutiveView._on_data_loaded(data)
        ├── Update 8 KPICard widgets (value + delta indicator)
        ├── ChartPanel.plot_cost_trend(...)
        ├── ChartPanel (pie): plot ABC distribution
        ├── DataTable: load top-5 risk products
        └── ChartPanel.plot_alert_history(...)
```

### 5.3 Compare Runs Modal Flow

```
User clicks [Compare Runs] in ExecutiveView
    │
    ▼
CompareRunsDialog (CTkToplevel)
    ├── Run 1 selector: [Run 1 (2026-02-20 18:55) ▼]
    ├── Run 2 selector: [Run 2 (latest future run) ▼]
    └── [Compare] button
            │
            ▼
    OptimizationService.compare_runs(run_id_1, run_id_2)
        └── Returns {portfolio_delta, product_deltas}
                │
                ▼
    CompareRunsDialog renders:
        ├── Portfolio Delta summary (cost_delta, alerts_delta, avg_ss_delta)
        └── DataTable: per-product SS/EOQ/ROP/cost before vs. after with % change
```

---

## 6. Report Design Details

### 6.1 Inventory Policy Report Layout (PDF)

**Page 1 — Cover:**
```
╔═══════════════════════════════════════════╗
║  LOGISTICS DSS                            ║
║  Inventory Policy Report                  ║
║                                           ║
║  Generated: 2026-02-20 19:05:42           ║
║  Optimization Run: #1 (2026-02-20 18:55) ║
║  Forecast Run: #1 (2026-02-20 14:07)      ║
║  Products: 20  |  Portfolio MAPE: 11.9%   ║
╚═══════════════════════════════════════════╝
```

**Page 2 — Portfolio KPI Table:**
8 KPI cells (2×4 grid): Total Annual Cost, Holding Cost, Ordering Cost, Active Alerts, A-Class Cost Share, Products Optimized, MAPE, Last Run Timestamp.

**Pages 3–N — Per-Product Policy Table (paginated):**
Columns: Rank, SKU, Product Name, ABC, Lead Time (d), SS (u), ROP (u), EOQ (u), Max Stock (u), Service Level, Ann. Order Cost ($), Ann. Hold Cost ($), Total Cost ($).
Sorted by `total_annual_cost DESC` (highest-cost products first).

**Page N+1 — ABC Cost Breakdown Chart:**
Stacked bar: A / B / C on x-axis; ordering cost and holding cost as stacked segments. Same chart as OptimizationView but embedded in PDF.

**Page N+2 — Alert Summary Table:**
Active unacknowledged alerts: SKU, Product, Alert Type, Severity, Current Stock, ROP, Suggested Order Qty, Days Until Stockout.

### 6.2 Executive Summary Report Layout (PDF, single page)

```
╔══════════════════════════════════════════════════════════════════╗
║  EXECUTIVE SUMMARY                           2026-02-20          ║
╠═══════════════╦══════════════╦══════════════╦══════════════════╣
║  20 Products  ║   $33,442    ║    11.9%     ║   1 CRITICAL     ║
║  Managed      ║  Annual Cost ║    MAPE      ║   Alert          ║
╠═══════════════╩══════════════╩══════════════╩══════════════════╣
║  [ABC Pie Chart — left half]   [Alert Bar Chart — right half]  ║
╠═══════════════════════════════════════════════════════════════  ╣
║  TOP-5 RISK PRODUCTS          ABC COST DISTRIBUTION            ║
║  SKU010 Gadget Ultra  CRIT    A: $24,306  (72.7%)              ║
║  SKU009 Gadget Lite   HIGH    B:  $7,031  (21.0%)              ║
║  SKU008 Gadget Max    EXCESS  C:  $2,105  ( 6.3%)              ║
╚══════════════════════════════════════════════════════════════════╝
```

Single-page format suitable for printing and presenting at board meetings without additional context.

### 6.3 Executive KPI Delta Computation

For each KPI, the delta is computed against the immediately prior `OptimizationRun`:

```python
def _compute_delta(current: float, prior: Optional[float],
                   positive_direction: str = "down") -> Tuple[Optional[float], str]:
    """
    positive_direction: "down" if lower is better (cost, MAPE, alerts)
                        "up"   if higher is better (products, service level)
    Returns (pct_change, direction) where direction ∈ {"up", "down", "stable"}
    """
    if prior is None or prior == 0:
        return None, "stable"
    pct = (current - prior) / abs(prior) * 100
    if abs(pct) < 0.5:               # below 0.5% treated as stable
        return pct, "stable"
    direction = "up" if current > prior else "down"
    return pct, direction
```

**Color mapping for KPICard delta indicator:**

| KPI | Positive (green) | Negative (red) |
|-----|------------------|----------------|
| `portfolio_annual_cost` | cost decreased (▼) | cost increased (▲) |
| `portfolio_mape` | MAPE decreased (▼) | MAPE increased (▲) |
| `active_critical_alerts` | alerts decreased (▼) | alerts increased (▲) |
| `excess_product_count` | excess decreased (▼) | excess increased (▲) |
| `stockout_product_count` | stockouts decreased (▼) | stockouts increased (▲) |

---

## 7. New Configuration Constants (`config/constants.py`)

| Constant | Default | Description |
|----------|---------|-------------|
| `REPORT_DEFAULT_EXPORT_DIR` | `"~/Documents/logistics_reports"` | Default directory for report file saves |
| `REPORT_DATE_FORMAT` | `"%Y-%m-%d"` | Date display format in all report headers |
| `REPORT_DATETIME_FORMAT` | `"%Y-%m-%d %H:%M"` | Full datetime format in report footers and history |
| `REPORT_CURRENCY_SYMBOL` | `"$"` | Currency prefix in PDF and Excel tables |
| `REPORT_LOG_RETENTION_DAYS` | `90` | Days to retain `ReportLog` entries before cleanup |
| `PDF_PAGE_SIZE` | `"A4"` | ReportLab page dimensions |
| `PDF_MARGIN_MM` | `20` | PDF page margin (all sides, mm) |
| `PDF_FONT_TITLE` | `"Helvetica-Bold"` | Cover page and heading font |
| `PDF_FONT_BODY` | `"Helvetica"` | Table cell and body font |
| `PDF_FONT_SIZE_TITLE` | `16` | Cover title font size (pt) |
| `PDF_FONT_SIZE_HEADING` | `12` | Section heading font size (pt) |
| `PDF_FONT_SIZE_BODY` | `9` | Table body font size (pt) |
| `PDF_TABLE_HEADER_COLOR` | `"#1f6aa5"` | Table header fill (blue, hex) |
| `PDF_TABLE_ROW_ALT_COLOR` | `"#f0f4f8"` | Alternating row fill (light blue-grey) |
| `EXCEL_MAX_ROWS_PER_SHEET` | `10000` | Maximum data rows per worksheet |
| `EXECUTIVE_TOP_RISK_PRODUCTS` | `5` | Top N stockout-risk products in Executive Dashboard |
| `EXECUTIVE_TREND_PERIODS` | `6` | Max prior optimization runs shown in cost trend chart |
| `EXECUTIVE_ALERT_HISTORY_WEEKS` | `4` | Weeks of alert history shown in alert history bar chart |
| `KPI_DELTA_STABLE_THRESHOLD_PCT` | `0.5` | Below this % change, delta direction = "stable" |
| `REPORT_PDF_MAX_TABLE_ROWS_PER_PAGE` | `28` | Rows per page in paginated PDF tables |

---

## 8. Technology Stack (Phase 6 Additions)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| PDF generation | reportlab | >= 4.0.0 | `Platypus` document model; `Table`, `Paragraph`, `Image`; ReportLab charts |
| Excel generation | openpyxl | >= 3.1.0 | Multi-sheet `.xlsx`; cell styles; `BarChart`/`PieChart` objects (likely already installed via pandas) |

**Updated `requirements.txt`:**
```
# Phase 6 - Executive Dashboard & Reporting
reportlab>=4.0.0
openpyxl>=3.1.0
```

**Note on openpyxl:** May already be installed as a pandas Excel engine. Phase 6 uses it directly (not through pandas) for fine-grained cell styling. The version requirement is tightened from pandas' implicit dependency.

---

## 9. Implementation Tasks

### 9.1 Database Extension (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 1 | Add Phase 6 constants to `config/constants.py` | `config/constants.py` | 20 min |
| 2 | Add `ReportLog` ORM model + 3 indexes | `src/database/models.py` | 30 min |

### 9.2 Reporting Engine (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 3 | Create `src/reporting/` package + `__init__.py` | `src/reporting/__init__.py` | 10 min |
| 4 | Implement `BaseReport` abstract class + `ReportMetadata` dataclass | `src/reporting/base_report.py` | 1 hour |
| 5 | Implement `PDFExporter` (all 4 report types + inline charts) | `src/reporting/pdf_exporter.py` | 6-8 hours |
| 6 | Implement `ExcelExporter` (all 4 report types + openpyxl charts) | `src/reporting/excel_exporter.py` | 4-6 hours |
| 7 | Implement `ReportRunner` (dispatch + validation + ReportLog persistence) | `src/reporting/report_runner.py` | 2-3 hours |

### 9.3 Service Layer (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 8 | Implement `ReportService` (executive KPIs + report log + risk products + trend data) | `src/services/report_service.py` | 3-4 hours |
| 9 | Extend `OptimizationService` with `compare_runs()` + `get_run_history()` | `src/services/optimization_service.py` | 2-3 hours |
| 10 | Extend `KPIService` with `get_executive_kpis()` + delta computation | `src/services/kpi_service.py` | 2 hours |

### 9.4 UI Extensions (Priority: Medium)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 11 | Add executive dashboard color constants to theme | `src/ui/theme.py` | 15 min |
| 12 | Add `plot_cost_trend()` and `plot_alert_history()` to `ChartPanel` | `src/ui/components/chart_panel.py` | 2-3 hours |
| 13 | Extend `KPICard` with delta indicator (▲/▼ % annotation) | `src/ui/components/kpi_card.py` | 1-2 hours |
| 14 | Implement `ExecutiveView` (4 sections + Compare Runs modal) | `src/ui/views/executive_view.py` | 5-7 hours |
| 15 | Implement `ReportsView` (3 sections + file dialog + history table) | `src/ui/views/reports_view.py` | 4-5 hours |
| 16 | Extend `DashboardView` with "Executive Summary →" shortcut link | `src/ui/views/dashboard_view.py` | 30 min |
| 17 | Extend `App` navigation: Executive + Reports buttons | `src/ui/app.py` | 30 min |

### 9.5 Testing (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 18 | PDF Exporter tests (7 tests) | `tests/test_pdf_exporter.py` | 2-3 hours |
| 19 | Excel Exporter tests (7 tests) | `tests/test_excel_exporter.py` | 2-3 hours |
| 20 | Report Runner tests (6 tests) | `tests/test_report_runner.py` | 2 hours |
| 21 | Report Service tests (7 tests) | `tests/test_report_service.py` | 2-3 hours |
| 22 | Executive KPI tests (6 tests) | `tests/test_executive_kpis.py` | 2 hours |
| 23 | Optimization compare_runs tests (6 tests) | `tests/test_optimization_compare.py` | 2 hours |

**Total estimated effort: 35-50 hours**

---

## 10. Implementation Order

The recommended build sequence validates the report engine against live data before integrating into the UI:

```
Step 1: Database Extension
  ├── Task 1:  Constants
  └── Task 2:  ReportLog model

Step 2: Reporting Engine Core (bottom-up)
  ├── Task 3:  Package setup
  ├── Task 4:  BaseReport + ReportMetadata
  ├── Task 5:  PDFExporter (start with POLICY type; add FORECAST, ALERT, EXECUTIVE)
  └── Task 6:  ExcelExporter (same order)

Step 3: Report Runner + ReportLog
  └── Task 7:  ReportRunner (dispatch + persistence)

Step 4: Service Layer
  ├── Task 8:  ReportService
  ├── Task 9:  OptimizationService.compare_runs() + get_run_history()
  └── Task 10: KPIService.get_executive_kpis() + delta computation

Step 5: Testing (verify immediately after each engine component)
  ├── Task 18: PDF tests              ← after Task 5
  ├── Task 19: Excel tests            ← after Task 6
  ├── Task 20: ReportRunner tests     ← after Task 7
  ├── Task 21: ReportService tests    ← after Task 8
  ├── Task 22: Executive KPI tests    ← after Task 10
  └── Task 23: compare_runs tests     ← after Task 9

Step 6: UI (build views last after logic is tested)
  ├── Task 11: Theme extensions
  ├── Task 12: ChartPanel extensions
  ├── Task 13: KPICard delta indicator
  ├── Task 14: ExecutiveView
  ├── Task 15: ReportsView
  ├── Task 16: DashboardView shortcut link
  └── Task 17: App navigation
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ReportLab API changes between versions (4.x vs 3.x) | High | Low | Pin `reportlab>=4.0.0` in requirements; test against installed version; abstract chart embedding behind `_build_chart()` helper |
| PDF generation with inline matplotlib charts produces oversized files (> 500 KB) | Medium | Medium | Render charts at `dpi=100` (not 150); use PNG compression; Executive Summary capped at 1 page; POLICY report budget: ≤ 5 pages |
| openpyxl chart objects not rendering correctly in all Excel versions | Medium | Medium | Fall back to data-only sheets if openpyxl chart rendering fails; document that charts require Excel 2016+ or LibreOffice 6+ |
| `compare_runs()` called with run_ids from different datasets (schema changed between runs) | Low | Low | Add guard: both runs must have the same `total_products`; raise `IncompatibleRunsError` if product counts differ |
| ExecutiveView loads slowly (> 3s) due to multiple DB queries on navigation | Medium | Medium | `_load_data()` runs in background thread; skeleton/placeholder KPI cards shown while loading; queries use indexed joins from Phase 5 |
| ReportLog grows unbounded on repeated report generation during testing | Low | Low | `REPORT_LOG_RETENTION_DAYS = 90` constant; Phase 6 adds cleanup helper `ReportService.purge_old_logs(days)` called on app startup |
| File save dialog blocks main thread (tkinter `filedialog`) | Low | Medium | `filedialog.asksaveasfilename()` called on main thread (required by tkinter); generation itself deferred to background thread only after path is confirmed |
| No optimization run exists when user opens ExecutiveView | High | Medium | Guard: show "No optimization data yet — run a forecast and optimization first" placeholder; all 4 KPI sections show "—" values |

---

## 12. Testing Strategy

### 12.1 PDF Exporter Tests (`tests/test_pdf_exporter.py`)

| Test | Validates |
|------|-----------|
| `test_pdf_policy_report_creates_file` | `render("POLICY", ...)` creates a file at `output_path`; file size > 1 KB |
| `test_pdf_policy_report_is_valid_pdf` | Output starts with `%PDF-` header bytes; valid PDF structure |
| `test_pdf_executive_report_single_page` | EXECUTIVE report PDF has exactly 1 page (verify via ReportLab page count metadata) |
| `test_pdf_forecast_report_contains_mape` | PDF text content (via `pypdf` or byte scan) contains "11.9" (portfolio MAPE) |
| `test_pdf_covers_all_products` | POLICY report text contains all 20 SKU codes from sample dataset |
| `test_pdf_null_unit_cost_no_exception` | Products with NULL `cost_price` do not raise exception; fallback value rendered |
| `test_pdf_empty_dataset_no_exception` | `gather_data()` on empty DB returns safe defaults; `render()` completes without crash |

### 12.2 Excel Exporter Tests (`tests/test_excel_exporter.py`)

| Test | Validates |
|------|-----------|
| `test_excel_policy_report_creates_file` | `render("POLICY", ...)` creates `.xlsx` file at `output_path` |
| `test_excel_policy_sheet_names` | Workbook has sheets: "Summary", "Policies", "Costs", "Alerts" |
| `test_excel_policies_row_count` | "Policies" sheet has header row + 20 data rows (one per product) |
| `test_excel_header_style` | "Policies" sheet row 1 cells have blue fill (`#1f6aa5`) and white bold font |
| `test_excel_currency_format` | Annual cost cells have number format `$#,##0.00` |
| `test_excel_forecast_sheet_names` | FORECAST report workbook has "Summary", "Accuracy", "Adequacy" sheets |
| `test_excel_alert_sheet_names` | ALERT report workbook has "Active" and "History" sheets |

### 12.3 Report Runner Tests (`tests/test_report_runner.py`)

| Test | Validates |
|------|-----------|
| `test_runner_persists_report_log` | After `generate()`: `report_logs` has 1 new row with `success=True` |
| `test_runner_log_records_duration` | `ReportLog.generation_seconds > 0` |
| `test_runner_log_records_file_size` | `ReportLog.file_size_bytes == os.path.getsize(output_path)` |
| `test_runner_invalid_type_raises` | `generate(report_type="INVALID", ...)` → raises `ValueError` |
| `test_runner_executive_excel_raises` | `generate("EXECUTIVE", "EXCEL", ...)` → raises `ValueError` (not supported) |
| `test_runner_failure_logged` | When `PDFExporter.render()` raises, `ReportLog.success=False` and `error_message` set |

### 12.4 Report Service Tests (`tests/test_report_service.py`)

| Test | Validates |
|------|-----------|
| `test_get_executive_kpis_all_keys` | Dict contains all 8 KPI keys + `*_delta` + `*_direction` keys |
| `test_get_executive_kpis_values` | `total_products == 20`, `portfolio_mape == 11.9` from fixture |
| `test_get_report_log_ordered` | Returns reports in `generated_at DESC` order |
| `test_get_top_risk_products_count` | Returns exactly `n` products (or fewer if fewer products exist) |
| `test_get_top_risk_products_order` | First product has smallest `days_until_stockout` |
| `test_get_cost_trend_values` | Returns one entry per optimization run; `total_annual_cost > 0` for each |
| `test_no_data_state` | All methods return safe defaults (empty lists / None values) on empty DB without exception |

### 12.5 Executive KPI Tests (`tests/test_executive_kpis.py`)

| Test | Validates |
|------|-----------|
| `test_executive_kpi_total_products` | `total_products == COUNT(products)` in fixture |
| `test_executive_kpi_portfolio_cost` | `portfolio_annual_cost == OptimizationRun.total_annual_cost` |
| `test_executive_kpi_critical_alerts` | `active_critical_alerts` matches unacknowledged CRITICAL alert count |
| `test_executive_kpi_delta_positive` | Cost decreased between runs → `portfolio_annual_cost_direction == "down"` (positive, green) |
| `test_executive_kpi_delta_stable` | < 0.5% change → `direction == "stable"` |
| `test_executive_kpi_no_prior_run` | First-ever run → all `*_delta = None`, all `*_direction = "stable"` |

### 12.6 Optimization Compare Tests (`tests/test_optimization_compare.py`)

| Test | Validates |
|------|-----------|
| `test_compare_runs_portfolio_delta` | `portfolio_delta["total_annual_cost_delta"] == run_2.total_annual_cost - run_1.total_annual_cost` |
| `test_compare_runs_product_count` | `len(product_deltas) == 20` (one entry per product in fixture) |
| `test_compare_runs_product_eoq_delta` | `product_delta["eoq_delta"] == eoq_run_2 - eoq_run_1` for a known product |
| `test_compare_runs_pct_change` | `cost_pct ≈ (cost_run_2 - cost_run_1) / cost_run_1 × 100` (within 0.01) |
| `test_get_run_history_ordered` | `get_run_history()` returns runs `run_timestamp DESC`; latest run first |
| `test_incompatible_runs_raises` | Two runs with different `total_products` → raises `IncompatibleRunsError` |

---

## 13. Non-Functional Requirements (Phase 6)

| Requirement | Target | Validation Method |
|-------------|--------|-------------------|
| Inventory Policy PDF generation time | < 8 seconds for 20 products | Timed in `test_pdf_policy_report_creates_file`; `ReportLog.generation_seconds` |
| Executive Summary PDF generation time | < 3 seconds | Single-page report; minimal data queries |
| Excel report generation time | < 5 seconds for 20 products | `test_excel_policy_report_creates_file` timing |
| PDF file size (Inventory Policy, 20 products) | < 500 KB | `os.path.getsize(output_path)` assertion in tests |
| Excel file size (Inventory Policy, 20 products) | < 200 KB | Same |
| ExecutiveView data load time | < 3 seconds | Background thread + timing log |
| compare_runs() response time | < 1 second | In-memory join of two runs' InventoryPolicy rows |
| Memory during PDF generation | < 50 MB additional | Matplotlib figures closed after PNG rendering (`plt.close(fig)`) |
| Report history table render time | < 0.5 seconds | In-memory DataTable; last 20 log entries only |

---

## 14. Phase 6 Exit Criteria

- [ ] `report_logs` table created; schema migration verified (`test_create_report_log` in test_database.py)
- [ ] `PDFExporter` generates a valid PDF for all 4 report types without exception (test: `test_pdf_policy_report_is_valid_pdf`)
- [ ] `ExcelExporter` generates a valid `.xlsx` with correct sheet names for all 4 report types (test: `test_excel_policy_sheet_names`)
- [ ] EXECUTIVE report type is PDF-only; `generate("EXECUTIVE", "EXCEL")` raises `ValueError` (test: `test_runner_executive_excel_raises`)
- [ ] `ReportRunner.generate()` persists a `ReportLog` row on success; sets `success=False` and `error_message` on failure
- [ ] `OptimizationService.compare_runs()` returns per-product delta table; `cost_pct` computed correctly (test: `test_compare_runs_pct_change`)
- [ ] `OptimizationService.get_run_history()` returns all runs ordered by `run_timestamp DESC`
- [ ] `KPIService.get_executive_kpis()` returns all 8 KPIs with correct values from live sample data
- [ ] Delta computation returns `direction="stable"` for changes < `KPI_DELTA_STABLE_THRESHOLD_PCT` (0.5%)
- [ ] `ExecutiveView` renders all 4 sections: headline KPI cards, cost trend chart, ABC pie, top-5 risk table + alert history bar
- [ ] KPICard delta indicator renders `▲`/`▼` with correct colour (green for "positive", red for "negative")
- [ ] `ReportsView` renders 3 sections; file save dialog pre-populates default filename; generation progress bar updates
- [ ] Opening `ReportsView` with no prior report history shows empty history table without exception
- [ ] Dashboard "Executive Summary →" shortcut navigates to ExecutiveView correctly
- [ ] All 6 new test modules pass with 100% success; 263 total tests passing
- [ ] Policy PDF file size < 500 KB for 20-product dataset; generation time < 8 seconds

---

## 15. Transition to Phase 7

Phase 7 (Supplier & Purchase Order Management) will extend Phase 6 reporting with operational procurement data:

1. **Purchase Order Tracking:**
   - New `PurchaseOrder` ORM model: `po_number`, `supplier_id`, `product_id`, `ordered_qty`, `unit_price`, `ordered_at`, `expected_arrival`, `received_at`, `actual_qty_received`
   - Phase 6 reports gain a "Purchase Orders" sheet/section once Phase 7 data is available
   - Phase 6's `ReportLog` becomes the audit trail for both report events and PO events

2. **Supplier Reliability Metrics:**
   - `actual_lead_time_days` on `Supplier` (recorded at each PO receipt) → `delivery_reliability_score` = fraction of on-time deliveries
   - Phase 6's `compare_runs()` extended to include `ss_delta` caused by lead time uncertainty changes: `SS = z × sqrt(L × σ_d² + D² × σ_L²)` (Wilson safety stock with lead time variance)
   - Phase 7 adds a Supplier Performance panel to the Executive Dashboard

3. **Automated Report Scheduling:**
   - Phase 7 may add a `ReportSchedule` model: cron-like triggers for weekly/monthly auto-generation
   - Phase 6 `ReportRunner` is already designed as a pure library call (no UI dependency) — Phase 7 can call it from a scheduler thread without modification

4. **Purchase Order Recommendations Integration:**
   - Phase 5's `suggested_order_qty` (currently informational) becomes an actionable `PurchaseOrder` draft in Phase 7
   - Phase 6's Alert History Report gains a "PO Generated" column once Phase 7 is live

**Prerequisites from Phase 6:**
- `ReportRunner.generate()` callable from non-UI code (no Tkinter dependencies in `src/reporting/`)
- `ReportLog` table available for PO event audit trail extension
- `ExecutiveView` layout reserved for a "Procurement" section (currently placeholder "—")
- `compare_runs()` framework extensible to include lead-time-sensitivity analysis

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-20 | Initial Phase 6 implementation plan |

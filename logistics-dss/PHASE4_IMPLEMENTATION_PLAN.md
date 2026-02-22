# Logistics DSS - Phase 4 Implementation Plan
# Demand Forecasting

**Project:** Logistics Decision Support System
**Phase:** 4 of 8 - Demand Forecasting
**Author:** Gilvan de Azevedo
**Date:** 2026-02-20
**Status:** Not Started
**Depends on:** Phase 3 (Analytics Engine) -- functionally complete

---

## 1. Phase 4 Objective

Build a demand forecasting engine that generates per-product daily demand predictions using statistical time-series models selected automatically based on Phase 3 ABC-XYZ classifications. This phase converts historical sales patterns into forward-looking demand estimates, enabling managers to anticipate replenishment needs, evaluate stock adequacy, and plan purchasing cycles before stockouts occur.

**Deliverables:**
- Forecasting engine with 4 model implementations (Moving Average, Croston's, Exponential Smoothing, Holt-Winters)
- Automatic model selection driven by ABC-XYZ class and data characteristics
- Walk-forward validation with MAPE, MAE, and RMSE accuracy metrics
- Persistent forecast storage (point forecasts + 95% confidence intervals per day)
- Forecast View (new screen: product selector, forecast chart with CI band, accuracy table)
- Analytics View integration (forecast accuracy panel alongside classification data)
- Full test suite covering all model implementations and accuracy calculations

---

## 2. Phase 3 Dependencies (Available)

Phase 4 builds directly on the following Phase 3 components:

| Component | Module | Usage in Phase 4 |
|-----------|--------|-------------------|
| ProductClassification model | `src/database/models.py` | ABC/XYZ class + avg_daily_demand as model selection input |
| ABCClassifier | `src/analytics/abc_classifier.py` | Prioritizes forecast effort (A = full tuning, C = simplified) |
| XYZClassifier | `src/analytics/xyz_classifier.py` | Drives model family selection (X→SES, Y→Holt-Winters, Z→MA/Croston) |
| TurnoverAnalyzer | `src/analytics/turnover_analyzer.py` | Baseline demand rate for model initialization |
| AnalyticsService | `src/services/analytics_service.py` | Classification data for model selector |
| SalesService | `src/services/sales_service.py` | Historical daily demand time series (training data) |
| InventoryService | `src/services/inventory_service.py` | Current stock levels for adequacy assessment |
| ChartPanel | `src/ui/components/chart_panel.py` | Extended with forecast + CI chart type |
| DataTable | `src/ui/components/data_table.py` | Forecast accuracy table |
| FilterBar | `src/ui/components/filter_bar.py` | Extended with forecast horizon and confidence selectors |
| ClassificationBadge | `src/ui/components/classification_badge.py` | Badge display in forecast product table |
| AnalyticsView | `src/ui/views/analytics_view.py` | Extended with forecast accuracy panel |
| DatabaseManager | `src/database/connection.py` | Sessions for forecast persistence |
| ORM Models | `src/database/models.py` | Extended with ForecastRun + DemandForecast models |
| LoggerMixin | `src/logger.py` | Logging across all new modules |
| Constants | `config/constants.py` | Extended with forecast horizon, confidence, and accuracy thresholds |

---

## 3. Architecture Overview

### 3.1 Phase 4 Directory Structure

```
logistics-dss/
├── config/
│   ├── settings.py             # (existing)
│   └── constants.py            # + forecast horizon, confidence level, accuracy thresholds
├── src/
│   ├── forecasting/            # NEW: Forecasting Engine
│   │   ├── __init__.py
│   │   ├── base_model.py           # Abstract base class for all forecast models
│   │   ├── moving_average.py       # Simple MA + Croston's (intermittent demand)
│   │   ├── exponential_smoothing.py # SES + Holt's Linear (statsmodels)
│   │   ├── holt_winters.py         # Holt-Winters additive (statsmodels)
│   │   ├── model_selector.py       # Chooses model based on XYZ class + data traits
│   │   ├── accuracy_evaluator.py   # Walk-forward validation, MAPE, MAE, RMSE
│   │   └── forecast_runner.py      # Orchestrates full forecast run + persistence
│   ├── services/               # (existing from Phases 2-3)
│   │   ├── inventory_service.py    # (existing)
│   │   ├── sales_service.py        # (existing)
│   │   ├── kpi_service.py          # + forecast KPI cards
│   │   ├── analytics_service.py    # (existing)
│   │   └── forecast_service.py     # NEW: query layer for forecast results
│   ├── database/
│   │   ├── connection.py           # (existing)
│   │   └── models.py               # + ForecastRun + DemandForecast models
│   └── ui/
│       ├── app.py                  # + Forecast nav entry
│       ├── theme.py                # + forecast color constants
│       ├── components/
│       │   ├── chart_panel.py      # + plot_forecast() with CI band
│       │   ├── filter_bar.py       # + horizon and confidence selectors
│       │   └── forecast_chart.py   # NEW: dedicated forecast + CI widget
│       └── views/
│           ├── analytics_view.py   # + Forecast Accuracy tab/panel
│           └── forecast_view.py    # NEW: Forecast management screen
├── tests/
│   ├── test_moving_average.py      # NEW: MA + Croston tests
│   ├── test_exponential_smoothing.py # NEW: SES + Holt's tests
│   ├── test_holt_winters.py        # NEW: Holt-Winters tests
│   ├── test_model_selector.py      # NEW: Model selection logic tests
│   ├── test_accuracy_evaluator.py  # NEW: MAPE, MAE, RMSE, walk-forward tests
│   └── test_forecast_service.py    # NEW: Forecast service integration tests
└── main.py                     # (existing)
```

### 3.2 Layer Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Dashboard   │  │  Inventory   │  │Analytics │  │  Forecast    │  │
│  │  View        │  │  View        │  │  View(+) │  │  View (NEW)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └──────┬───────┘  │
│         │                 │               │                │          │
│  ┌──────┴─────────────────┴───────────────┴────────────────┴────────┐  │
│  │              Reusable Components (+ extensions)                  │  │
│  │  KPI Card | DataTable | ChartPanel(+) | Badge | ForecastChart(N)│  │
│  └──────────────────────────┬─────────────────────────────────────  ┘  │
├─────────────────────────────┼─────────────────────────────────────────┤
│                       Service Layer                                    │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Inventory  │  │   Sales    │  │  Analytics   │  │  Forecast    │   │
│  │ Service    │  │   Service  │  │  Service     │  │  Service(NEW)│   │
│  └────────────┘  └─────┬──── ┘  └──────────────┘  └──────┬───────┘   │
├────────────────────────┼──────────────────────────────────┼───────────┤
│                  Forecasting Engine (NEW)                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     ForecastRunner                               │   │
│  │   ┌─────────────────────────────────────────────────────────┐   │   │
│  │   │                  ModelSelector                           │   │   │
│  │   └──────┬────────────────┬──────────────────┬──────────────┘   │   │
│  │          │                │                  │                  │   │
│  │  ┌───────┴──────┐  ┌──────┴──────┐  ┌───────┴───────────────┐  │   │
│  │  │ MovingAverage│  │Exponential  │  │    HoltWinters        │  │   │
│  │  │ + Croston's  │  │Smoothing    │  │    (Trend+Seasonal)   │  │   │
│  │  │ (for Z-class)│  │(SES/Holt's) │  │    (for Y-class)      │  │   │
│  │  └──────────────┘  └─────────────┘  └───────────────────────┘  │   │
│  │                   AccuracyEvaluator                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────── ┤
│               Analytics Engine (Phase 3) + Data Layer (Phases 1-2)    │
│  ┌──────────────────┐  ┌──────────────────────────────┐  ┌──────────┐  │
│  │ Classification   │  │  ORM Models                  │  │  Sales   │  │
│  │ (ABC/XYZ)        │  │  (+ ForecastRun, Demand-     │  │  Records │  │
│  │                  │  │    Forecast)                 │  │  (train) │  │
│  └──────────────────┘  └──────────────────────────────┘  └──────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Database Model Extension

#### 4.1.1 ForecastRun (`src/database/models.py`)

Audit header for each full portfolio forecast execution:

```python
class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id                   = Column(Integer, primary_key=True)
    run_timestamp        = Column(DateTime, default=func.now())
    forecast_horizon     = Column(Integer, nullable=False)   # days ahead
    confidence_level     = Column(Float, nullable=False)     # e.g. 0.95
    lookback_days        = Column(Integer, nullable=False)   # training window
    total_products       = Column(Integer, nullable=False)
    successful_forecasts = Column(Integer, nullable=False)
    failed_forecasts     = Column(Integer, nullable=False)
    portfolio_mape       = Column(Float, nullable=True)      # weighted avg MAPE
    portfolio_mae        = Column(Float, nullable=True)
    notes                = Column(Text, nullable=True)

    forecasts = relationship("DemandForecast", back_populates="run")
```

#### 4.1.2 DemandForecast (`src/database/models.py`)

One row per product per forecast date, storing point forecast and confidence bounds:

```python
class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id               = Column(Integer, primary_key=True)
    run_id           = Column(Integer, ForeignKey("forecast_runs.id"), nullable=False)
    product_id       = Column(Integer, ForeignKey("products.id"), nullable=False)
    model_name       = Column(String(50), nullable=False)   # "SES", "HoltWinters", etc.
    forecast_date    = Column(Date, nullable=False)
    predicted_qty    = Column(Float, nullable=False)        # point forecast (units/day)
    lower_ci         = Column(Float, nullable=False)        # lower confidence bound
    upper_ci         = Column(Float, nullable=False)        # upper confidence bound
    mape             = Column(Float, nullable=True)         # validation MAPE (%)
    mae              = Column(Float, nullable=True)         # validation MAE
    rmse             = Column(Float, nullable=True)         # validation RMSE
    is_validated     = Column(Boolean, default=False)       # True if holdout tested
    generated_at     = Column(DateTime, default=func.now())

    run     = relationship("ForecastRun", back_populates="forecasts")
    product = relationship("Product", back_populates="forecasts")
```

**Indexes:**
- `(product_id, forecast_date)` -- fast per-product date range queries
- `(run_id, product_id)` -- fast per-run product retrieval
- `(product_id, run_id DESC)` -- latest run per product

---

### 4.2 Forecasting Engine

#### 4.2.1 Base Model (`src/forecasting/base_model.py`)

Abstract base class defining the contract for all forecast models:

```python
@dataclass
class ForecastOutput:
    model_name:       str
    product_id:       int
    horizon_days:     int
    forecast_dates:   List[date]
    predicted_qty:    List[float]   # point forecast (clipped to >= 0)
    lower_ci:         List[float]   # lower confidence bound (clipped to >= 0)
    upper_ci:         List[float]   # upper confidence bound
    mape:             Optional[float]
    mae:              Optional[float]
    rmse:             Optional[float]
    confidence_level: float
    training_days:    int           # actual days used (may be < requested)
    warnings:         List[str]

class BaseForecastModel(ABC, LoggerMixin):
    @abstractmethod
    def fit(self, series: pd.Series) -> "BaseForecastModel": ...

    @abstractmethod
    def predict(self, horizon: int, confidence: float) -> ForecastOutput: ...

    @abstractmethod
    def get_model_name(self) -> str: ...

    def get_fitted_values(self) -> Optional[pd.Series]: ...
    def is_fitted(self) -> bool: ...
```

**`ForecastOutput` contract:**
- `predicted_qty` values are clipped to `>= 0` (demand cannot be negative)
- `lower_ci` values are clipped to `>= 0`
- All date lists are aligned: `forecast_dates[i]` corresponds to `predicted_qty[i]`
- `mape`, `mae`, `rmse` are `None` if walk-forward validation was not performed

---

#### 4.2.2 Moving Average Model (`src/forecasting/moving_average.py`)

**Purpose:** Baseline model for Z-class products (erratic, unpredictable demand). Two implementations in one module: standard Moving Average and Croston's method for intermittent demand.

**`MovingAverageModel`:**

Algorithm:
```
1. Compute mean and std of last `window` days of demand:
      mean_demand = MEAN(series[-window:])
      std_demand  = STD(series[-window:], ddof=1)

2. Point forecast: constant at mean_demand for all horizon days

3. Confidence interval (t-distribution, df = window - 1):
      t_crit = scipy.stats.t.ppf((1 + confidence) / 2, df=window-1)
      CI_half = t_crit * std_demand / sqrt(window)
      lower_ci = max(0, mean_demand - CI_half)
      upper_ci = mean_demand + CI_half
```

**Properties:**
- `window`: look-back window (default: `MA_WINDOW_DAYS` constant, default 14)
- Falls back to available data length if `len(series) < window`
- Wide CI reflects genuine unpredictability of Z-class products

**`CrostonModel`:**

Algorithm (Syntetos-Boylan Approximation, SBA):
```
Definitions:
  demand_occasions = days WHERE qty > 0
  inter-demand_intervals = gaps between demand occasions
  demand_sizes = qty values on demand occasions only

SBA forecast:
  alpha = CROSTON_ALPHA (default 0.1)
  z_hat = exponential smoothing of demand_sizes
  p_hat = exponential smoothing of inter-demand intervals
  forecast_rate = (1 - alpha/2) * (z_hat / p_hat)   per day

CI: simulate demand process (Bernoulli arrival × Poisson size)
    over N Monte Carlo trials → use alpha/2 and 1-alpha/2 percentiles
```

**Applicable when:** `zero_demand_ratio >= CROSTON_ZERO_THRESHOLD` (default: 0.50 — at least 50% of days had zero demand).

**Methods:**

| Method | Description |
|--------|-------------|
| `fit(series)` | Computes z_hat, p_hat; stores internal state |
| `predict(horizon, confidence)` | Returns constant SBA rate with Monte Carlo CI |
| `get_zero_demand_ratio(series)` | Static: fraction of zero-demand days |

---

#### 4.2.3 Exponential Smoothing Model (`src/forecasting/exponential_smoothing.py`)

**Purpose:** Primary model for X-class products (stable demand). Uses `statsmodels.tsa.holtwinters.ExponentialSmoothing`.

**Two sub-modes selected automatically by AIC:**

| Mode | Trend | Seasonal | Use Case |
|------|-------|----------|----------|
| SES (Simple) | None | None | Level-stationary demand (no growth, no seasonality) |
| Holt's Linear | Additive | None | Demand with consistent upward or downward trend |

**Algorithm:**
```
1. Fit SES:  ExponentialSmoothing(series, trend=None).fit()  → AIC_ses
2. Fit Holt: ExponentialSmoothing(series, trend='add').fit()  → AIC_holt
3. Select model with lower AIC
4. Generate forecast: model.forecast(horizon)
5. Compute CI from residual standard error:
      σ_residual = STD(model.resid)
      z_crit     = scipy.stats.norm.ppf((1 + confidence) / 2)
      CI_half[h] = z_crit * σ_residual * sqrt(h)   (grows with horizon)
      lower_ci   = max(0, forecast - CI_half)
      upper_ci   = forecast + CI_half
```

**Properties:**
- Requires `>= FORECAST_MIN_TRAINING_DAYS` (default: 14) data points
- Falls back to `MovingAverageModel` if insufficient data
- AIC comparison penalizes Holt's complexity; SES preferred unless trend is clear
- Smoothing parameters (alpha, beta) optimized by statsmodels MLE

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `fit(series)` | `self` | Fits both SES and Holt's, selects by AIC |
| `predict(horizon, confidence)` | `ForecastOutput` | Forecast with growing CI |
| `get_selected_mode()` | `str` | "SES" or "Holt's Linear" |
| `get_aic()` | `float` | AIC of selected model |
| `get_params()` | `Dict` | Alpha, beta, initial values |

---

#### 4.2.4 Holt-Winters Model (`src/forecasting/holt_winters.py`)

**Purpose:** Primary model for Y-class products (seasonal or trending demand). Uses `statsmodels.tsa.holtwinters.ExponentialSmoothing` with trend and seasonal components.

**Configuration:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `trend` | `'add'` | Additive trend (absolute growth per period) |
| `seasonal` | `'add'` | Additive seasonality (absolute seasonal effect) |
| `seasonal_periods` | `7` | Weekly cycle (daily demand data) |
| `initialization_method` | `'estimated'` | Statsmodels estimates initial state from data |

**Algorithm:**
```
1. Check data sufficiency: len(series) >= 2 * seasonal_periods (>= 14 days)
   If insufficient → fall back to ExponentialSmoothingModel

2. Fit HoltWinters: ExponentialSmoothing(
       series,
       trend='add',
       seasonal='add',
       seasonal_periods=7
   ).fit(optimized=True)

3. Generate forecast: model.forecast(horizon)

4. Compute CI via simulation:
      simulated = model.simulate(horizon, repetitions=N_SIM, random_errors='bootstrap')
      lower_ci  = np.percentile(simulated, (1 - confidence) / 2 * 100, axis=1)
      upper_ci  = np.percentile(simulated, (1 + confidence) / 2 * 100, axis=1)
      lower_ci  = np.clip(lower_ci, 0, None)
```

**Seasonal period detection:** `seasonal_periods=7` is the default for daily data with weekly cycles. If a product has `data_length < 21` (< 3 full weekly cycles), fall back to `ExponentialSmoothingModel` rather than risk unreliable seasonal estimation.

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `fit(series)` | `self` | Fits Holt-Winters model with statsmodels MLE optimization |
| `predict(horizon, confidence)` | `ForecastOutput` | Forecast with simulation-based CI |
| `get_seasonal_factors()` | `List[float]` | 7 daily seasonal indices (Mon-Sun) |
| `get_params()` | `Dict` | Alpha, beta, gamma, initial values |
| `get_aic()` | `float` | AIC of fitted model |

---

#### 4.2.5 Model Selector (`src/forecasting/model_selector.py`)

**Purpose:** Chooses the appropriate forecast model for each product based on its ABC-XYZ classification, data length, and demand pattern characteristics.

**Selection Decision Tree:**

```
INPUT: xyz_class, abc_class, data_length, zero_demand_ratio, series

Step 1 -- Data sufficiency check:
    if data_length < FORECAST_MIN_TRAINING_DAYS (14):
        → MovingAverageModel (only model robust to very short series)
        → warning: "Insufficient data; using Moving Average"

Step 2 -- Z-class routing (erratic demand):
    if xyz_class == "Z":
        if zero_demand_ratio >= CROSTON_ZERO_THRESHOLD (0.50):
            → CrostonModel (intermittent demand)
        else:
            → MovingAverageModel (erratic but not intermittent)

Step 3 -- Y-class routing (variable demand):
    if xyz_class == "Y":
        if data_length >= 2 * SEASONAL_PERIODS (14):
            → HoltWintersModel (handles trend + weekly seasonality)
        else:
            → ExponentialSmoothingModel (SES/Holt's; fallback)

Step 4 -- X-class routing (stable demand):
    if xyz_class == "X":
        → ExponentialSmoothingModel (SES or Holt's, selected by AIC)

Step 5 -- ABC class modifies validation depth (not model choice):
    A → full walk-forward validation (FORECAST_VALIDATION_DAYS holdout)
    B → standard validation (FORECAST_VALIDATION_DAYS / 2 holdout)
    C → no validation (skip accuracy computation for speed)
```

**ABC-XYZ Model Assignment Matrix:**

```
         X (stable)            Y (variable)          Z (erratic)
    ┌──────────────────────┬──────────────────────┬─────────────────────┐
  A │ ExponentialSmoothing │   HoltWinters        │ Croston / MA        │
    │ (full validation)    │   (full validation)  │ (full validation)   │
    ├──────────────────────┼──────────────────────┼─────────────────────┤
  B │ ExponentialSmoothing │   HoltWinters        │ Croston / MA        │
    │ (half validation)    │   (half validation)  │ (half validation)   │
    ├──────────────────────┼──────────────────────┼─────────────────────┤
  C │ ExponentialSmoothing │   HoltWinters        │ MovingAverage       │
    │ (no validation)      │   (no validation)    │ (no validation)     │
    └──────────────────────┴──────────────────────┴─────────────────────┘
```

**Class `ModelSelector`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `select(product_id, classification, series)` | `BaseForecastModel` | Returns fitted model instance |
| `get_model_name(xyz_class, zero_ratio, data_len)` | `str` | Model name without fitting |
| `get_validation_days(abc_class)` | `int` | Holdout days based on ABC priority |

---

#### 4.2.6 Accuracy Evaluator (`src/forecasting/accuracy_evaluator.py`)

**Purpose:** Measures forecast accuracy via walk-forward (expanding window) validation on historical data. Runs before generating the live forecast so accuracy metrics are always based on held-out actuals.

**Walk-Forward Validation:**

```
Given series of length N and validation_days = k:

Training set:  series[:N-k]   (first N-k days)
Test set:      series[N-k:]   (last k days)

Procedure:
  1. Fit model on training set
  2. Forecast k days ahead
  3. Compare forecast[0:k] with test[0:k]
  4. Compute metrics
```

**Accuracy Metrics:**

| Metric | Formula | Notes |
|--------|---------|-------|
| **MAPE** | `MEAN(|actual - forecast| / actual) * 100` | Skips periods where `actual == 0` to avoid division by zero |
| **sMAPE** | `MEAN(2*|actual - forecast| / (|actual| + |forecast|)) * 100` | Symmetric; handles zeros; supplementary metric |
| **MAE** | `MEAN(|actual - forecast|)` | Units of demand; interpretable |
| **RMSE** | `SQRT(MEAN((actual - forecast)²))` | Penalizes large errors; used for safety stock sizing |

**Class `AccuracyEvaluator`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `evaluate(model_class, series, validation_days, confidence)` | `AccuracyResult` | Fits on train split, forecasts, computes all metrics |
| `compute_mape(actual, forecast)` | `Optional[float]` | Returns None if all actuals are zero |
| `compute_smape(actual, forecast)` | `float` | Symmetric MAPE |
| `compute_mae(actual, forecast)` | `float` | Mean absolute error |
| `compute_rmse(actual, forecast)` | `float` | Root mean squared error |

**`AccuracyResult` dataclass:**

```python
@dataclass
class AccuracyResult:
    mape:          Optional[float]   # None if no non-zero actuals
    smape:         float
    mae:           float
    rmse:          float
    validation_days: int
    actual_values:   List[float]
    forecast_values: List[float]
```

**MAPE interpretation thresholds** (to add to `config/constants.py`):

| Constant | Default | Meaning |
|----------|---------|---------|
| `FORECAST_MAPE_EXCELLENT` | 10.0 | MAPE ≤ 10% → green (excellent accuracy) |
| `FORECAST_MAPE_ACCEPTABLE` | 20.0 | MAPE ≤ 20% → amber (acceptable) |
| — | > 20.0 | MAPE > 20% → red (poor; use with caution) |

---

#### 4.2.7 Forecast Runner (`src/forecasting/forecast_runner.py`)

**Purpose:** Orchestrates a full portfolio forecast run: retrieves classifications, builds demand series, selects and fits models, evaluates accuracy, generates predictions, and persists results atomically.

**Class `ForecastRunner`:**

| Method | Returns | Description |
|--------|---------|-------------|
| `run(horizon_days, confidence, lookback_days)` | `ForecastReport` | Full portfolio run; persists ForecastRun + DemandForecast rows |
| `run_product(product_id, horizon_days, confidence, lookback_days)` | `ForecastOutput` | Single-product forecast (no DB persistence) |
| `get_last_run_timestamp()` | `Optional[datetime]` | MAX(run_timestamp) from forecast_runs |

**`run()` execution sequence:**

```
1. Load all ProductClassification records (latest per product)
   via AnalyticsService.get_all_classifications()

2. For each product (ordered by ABC class: A first):

   a. Build demand series:
        series = SalesService.get_daily_demand_series(product_id, lookback_days)
        series = fill_missing_dates(series, 0)   # same as XYZ preparation

   b. Select model:
        model_instance = ModelSelector.select(product_id, classification, series)

   c. Evaluate accuracy (based on ABC class):
        if validation_days > 0:
            accuracy = AccuracyEvaluator.evaluate(
                type(model_instance), series, validation_days, confidence)
        else:
            accuracy = None

   d. Refit on full series (after holdout validation):
        model_instance.fit(series)

   e. Generate forecast:
        output = model_instance.predict(horizon_days, confidence)
        output.mape  = accuracy.mape  if accuracy else None
        output.mae   = accuracy.mae   if accuracy else None
        output.rmse  = accuracy.rmse  if accuracy else None

   f. Collect ForecastOutput

3. Compute portfolio_mape = weighted MAPE (weighted by ABC revenue share)

4. Persist:
   forecast_run = ForecastRun(...)
   session.add(forecast_run)
   session.flush()   # get run_id

   for output in all_outputs:
       for i, date in enumerate(output.forecast_dates):
           session.add(DemandForecast(
               run_id=forecast_run.id, product_id=..., model_name=...,
               forecast_date=date, predicted_qty=output.predicted_qty[i],
               lower_ci=output.lower_ci[i], upper_ci=output.upper_ci[i],
               mape=output.mape, mae=output.mae, rmse=output.rmse,
               is_validated=(output.mape is not None)
           ))

   session.commit()

5. Return ForecastReport
```

**`ForecastReport` dataclass:**

```python
@dataclass
class ForecastReport:
    run_id:               int
    run_timestamp:        datetime
    horizon_days:         int
    confidence_level:     float
    total_products:       int
    successful_forecasts: int
    failed_forecasts:     int
    portfolio_mape:       Optional[float]
    portfolio_mae:        Optional[float]
    model_usage:          Dict[str, int]   # {"SES": 8, "HoltWinters": 7, ...}
    outputs:              List[ForecastOutput]
    warnings:             List[str]
```

---

### 4.3 Forecast Service (`src/services/forecast_service.py`)

**Purpose:** Query layer for forecast results — reads persisted `DemandForecast` rows, provides aggregated and filtered views for the UI.

| Method | Returns | Description |
|--------|---------|-------------|
| `get_forecast(product_id, run_id)` | `List[Dict]` | All forecast dates + predicted_qty + CI for a product |
| `get_latest_forecast(product_id)` | `List[Dict]` | Forecast from the most recent run for a product |
| `get_forecast_summary()` | `List[Dict]` | Per-product summary: model used, MAPE, horizon, run_timestamp |
| `get_accuracy_table()` | `List[Dict]` | All products with MAPE, MAE, RMSE, model name, last run |
| `get_portfolio_mape()` | `Optional[float]` | Weighted MAPE of latest run |
| `get_last_run_timestamp()` | `Optional[datetime]` | When the most recent run was completed |
| `get_demand_series(product_id, days)` | `List[Dict]` | Historical daily actuals (for chart overlay) |
| `run_forecast(horizon, confidence, lookback)` | `ForecastReport` | Delegates to ForecastRunner.run() |
| `run_forecast_product(product_id, horizon, confidence, lookback)` | `ForecastOutput` | Single-product re-forecast |

---

### 4.4 Presentation Layer

#### 4.4.1 Theme Extensions (`src/ui/theme.py`)

New forecast color constants:

| Constant | Value | Usage |
|----------|-------|-------|
| `COLOR_FORECAST_LINE` | `"#5b8dee"` | Forecast line (dashed blue) |
| `COLOR_FORECAST_CI` | `"#5b8dee"` | CI band fill (same blue, lower alpha) |
| `COLOR_ACTUAL_LINE` | `"#2fa572"` | Historical actuals line (green) |
| `COLOR_TODAY_LINE` | `"#e8a838"` | Vertical "today" marker (amber) |
| `COLOR_MAPE_EXCELLENT` | `"#2fa572"` | MAPE ≤ 10% badge (green) |
| `COLOR_MAPE_ACCEPTABLE` | `"#e8a838"` | MAPE ≤ 20% badge (amber) |
| `COLOR_MAPE_POOR` | `"#d64545"` | MAPE > 20% badge (red) |

---

#### 4.4.2 Forecast Chart (`src/ui/components/forecast_chart.py`)

A specialized Matplotlib widget for rendering historical actuals overlaid with forecast + confidence interval:

**Visual layout:**
```
Qty │  ──────────────────── actual (solid green)
    │                    ┊  - - - - forecast (dashed blue)
    │                    ┊  ░░░░░░░░ 95% CI (blue fill, 20% alpha)
    │                    ┊
    └────────────────────┊────────────────────────
     historical           today      forecast horizon
```

**Properties:**
- `show_ci`: toggle confidence interval band (default: True)
- `show_actuals`: toggle historical line (default: True)
- `confidence_label`: display string for CI legend (e.g., "95% CI")
- `horizon_days`: used to right-size the x-axis

**Methods:**

| Method | Description |
|--------|-------------|
| `plot(actual_dates, actual_qty, forecast_dates, predicted_qty, lower_ci, upper_ci, title)` | Full render with both actuals and forecast |
| `plot_forecast_only(forecast_dates, predicted_qty, lower_ci, upper_ci, title)` | For products with no historical actuals available |
| `set_mape_annotation(mape, model_name)` | Adds accuracy annotation box to chart corner |
| `clear()` | Reset canvas |

---

#### 4.4.3 ChartPanel Extension (`src/ui/components/chart_panel.py`)

New method added to the existing ChartPanel:

```python
def plot_forecast(self, actual_dates, actual_qty,
                  forecast_dates, predicted_qty,
                  lower_ci, upper_ci, title,
                  confidence=0.95, model_name=None, mape=None):
    """
    Renders historical actuals + forecast line + CI band on a single axis.
    Draws a vertical dashed line at today separating actuals from forecast.
    """
```

---

#### 4.4.4 FilterBar Extensions (`src/ui/components/filter_bar.py`)

New optional controls (enabled via `show_forecast_filters=True`):

- **Forecast Horizon** `CTkOptionMenu`: [14 days / 30 days / 60 days / 90 days]
- **Confidence Level** `CTkOptionMenu`: [80% / 90% / 95%]
- `get_filters()` extended with `horizon_days: int` and `confidence_level: float`

---

#### 4.4.5 Forecast View (`src/ui/views/forecast_view.py`)

New dedicated screen for forecast management:

```
┌──────────────────────────────────────────────────────────────────────┐
│  FILTER BAR  [Category ▼]  [ABC Class ▼]  [XYZ Class ▼]             │
│              [Horizon: 30 days ▼]  [Confidence: 95% ▼]  [Run ↻]     │
├──────────────────────────────────────────────────────────────────────┤
│  SUMMARY CARDS                                                        │
│  ┌───────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │Forecasted │  │Portfolio  │  │ Insufficient│  │ Last Forecast    │  │
│  │ Products  │  │   MAPE    │  │   Data      │  │ 2026-02-20 11:45 │  │
│  │    20     │  │   8.3%    │  │     2       │  │  30-day horizon  │  │
│  └───────────┘  └───────────┘  └────────────┘  └──────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  ACCURACY TABLE (top half)    │  FORECAST CHART (right / top half)   │
│  ┌──────┬──────────┬──┬──┬──────┬──────────┐  │  ┌──────────────────┐│
│  │ SKU  │ Name     │AB│XY│Model │  MAPE    │  │  │ SKU020           ││
│  ├──────┼──────────┼──┼──┼──────┼──────────┤  │  │ LED Monitor      ││
│  │SK020 │ LED Mon  │A │X │ SES  │  5.2% ● │  │  │ Model: SES       ││
│  │SK008 │ Gadget M │A │X │ SES  │  6.8% ● │  │  │ MAPE: 5.2%       ││
│  │SK010 │ Gadget U │A │Z │ MA   │ 18.4% ● │  │  │                  ││
│  │SK011 │ Power Dr │A │Y │ HW   │  9.1% ● │  │  │ ──── actual      ││
│  │  ... │ ...      │..│..│  ... │   ...   │  │  │ - - forecast     ││
│  └──────┴──────────┴──┴──┴──────┴──────────┘  │  │ ░░░ 95% CI      ││
│                                                │  └──────────────────┘│
├────────────────────────────────────────────────────────────────────── ┤
│  DEMAND ADEQUACY TABLE (bottom half)                                  │
│  ┌────────┬──────────────┬───────┬──────────┬──────────┬───────────┐  │
│  │  SKU   │ Product      │ Stock │ Forecast │ Coverage │  Status   │  │
│  │        │              │ Units │ Total    │ (days)   │           │  │
│  ├────────┼──────────────┼───────┼──────────┼──────────┼───────────┤  │
│  │ SK020  │ LED Monitor  │  145  │  85 units│  51 days │  OK       │  │
│  │ SK010  │ Gadget Ultra │    0  │  38 units│   0 days │  STOCKOUT │  │
│  │ SK013  │ Tool Basic   │  200  │   6 units│ 180 days │  EXCESS   │  │
│  └────────┴──────────────┴───────┴──────────┴──────────┴───────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Four sections:**

1. **Filter Bar** with forecast-specific controls (horizon, confidence, ABC/XYZ filter, category, "Run Forecast" button)
2. **Summary Cards:** Forecasted Products, Portfolio MAPE (color-coded), Insufficient Data count, Last Run timestamp
3. **Accuracy Table + Forecast Chart** (side-by-side):
   - Left: sortable accuracy table (SKU, Name, ABC badge, XYZ badge, Model, MAPE colored badge)
   - Right: `ForecastChart` widget showing selected product; updates on row click
4. **Demand Adequacy Table:** per-product stock sufficiency against forecast demand:
   - `coverage_days = current_stock / mean_forecast_daily_demand`
   - Status: STOCKOUT (stock=0), OK (coverage ≥ 14 days), WARNING (7-13 days), CRITICAL (0-6 days), EXCESS (> 90 days)

**Background thread implementation (same pattern as AnalyticsView):**
```python
def _run_forecast(self):
    self._set_running_state(True)
    thread = threading.Thread(target=self._forecast_worker, daemon=True)
    thread.start()

def _forecast_worker(self):
    report = self.forecast_service.run_forecast(
        self.horizon_days, self.confidence_level, self.lookback_days)
    self.after(0, lambda: self._on_forecast_complete(report))
```

---

#### 4.4.6 Analytics View Extension (`src/ui/views/analytics_view.py`)

New **Forecast Accuracy Panel** added as an additional section at the bottom of the existing Analytics View:

```
┌──────────────────────────────────────────────────────────────────────┐
│  FORECAST ACCURACY (from latest run)                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Portfolio MAPE: 8.3%   ●  Excellent (<10%)  [View All →]        │  │
│  │                                                                  │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │ MAPE by ABC Class (grouped bar)                          │   │  │
│  │  │  A: 7.2%  B: 9.1%  C: 14.6%  (weighted avg by class)   │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

- Shows only if a forecast run exists (gracefully hidden otherwise)
- "View All →" button navigates to the full Forecast View

---

#### 4.4.7 App Navigation (`src/ui/app.py`)

- Add **"Forecast"** nav button to sidebar (5th button, between Analytics and Import)
- `ForecastView` instantiated lazily on first click
- `_on_import_complete()` callback does NOT auto-trigger forecast refresh (forecast runs are manual)

---

## 5. Data Flow

### 5.1 Forecast Run Sequence

```
User clicks "Run Forecast" in Forecast View
    │
    ▼
ForecastView._run_forecast()
    │ (background thread)
    ▼
ForecastRunner.run(horizon=30, confidence=0.95, lookback=90)
    │
    ├── AnalyticsService.get_all_classifications()
    │       └── 20 products with ABC/XYZ class + avg_daily_demand
    │
    ├── For each product (ABC priority order: A→B→C):
    │       │
    │       ├── SalesService.get_daily_demand_series(product_id, 90)
    │       │       └── Pandas Series: date_index → daily_qty (90 days, zeros filled)
    │       │
    │       ├── ModelSelector.select(product_id, classification, series)
    │       │       └── Returns fitted model instance
    │       │
    │       ├── AccuracyEvaluator.evaluate(model_class, series, validation_days)
    │       │       └── Walk-forward: train on [:N-k], predict k, compare
    │       │       └── AccuracyResult (MAPE, MAE, RMSE)
    │       │
    │       ├── model_instance.fit(series)     ← refit on FULL series
    │       │
    │       └── model_instance.predict(30, 0.95)
    │               └── ForecastOutput (30 dates, predicted_qty, lower/upper CI)
    │
    ├── Compute portfolio_mape (weighted by revenue share from ABC)
    │
    ├── Persist ForecastRun + DemandForecast rows
    │       └── session.commit()
    │
    └── Return ForecastReport
            │ (main thread via after())
            ▼
    ForecastView._on_forecast_complete(report)
        ├── Update summary KPI cards
        ├── Reload accuracy table
        ├── Reload demand adequacy table
        └── Refresh chart for currently selected product
```

### 5.2 Chart Render Sequence

```
User clicks row in accuracy table (e.g., SKU020)
    │
    ▼
ForecastView._on_product_select(product_id=20)
    │
    ├── ForecastService.get_latest_forecast(product_id=20)
    │       └── List[Dict]: forecast_date, predicted_qty, lower_ci, upper_ci
    │
    ├── ForecastService.get_demand_series(product_id=20, days=60)
    │       └── List[Dict]: date, actual_qty (historical)
    │
    └── ForecastChart.plot(
            actual_dates, actual_qty,
            forecast_dates, predicted_qty, lower_ci, upper_ci,
            title="SKU020 - LED Monitor",
            model_name="SES", mape=5.2
        )
```

### 5.3 Adequacy Check Sequence

```
ForecastView._compute_adequacy(products, forecasts, inventory)
    │
    ├── InventoryService.get_stock_summary()
    │       └── Current stock per product
    │
    ├── For each product:
    │       mean_daily_forecast = AVG(predicted_qty) over horizon
    │       coverage_days = current_stock / mean_daily_forecast
    │           (0 if stock=0; ∞ shown as 999 if mean_forecast=0)
    │
    │       status:
    │           stock == 0        → STOCKOUT
    │           coverage < 7     → CRITICAL
    │           coverage < 14    → WARNING
    │           coverage > 90    → EXCESS
    │           else             → OK
    │
    └── Load adequacy table with status color coding
```

---

## 6. Forecasting Model Details

### 6.1 Moving Average & Croston's Method

**When Croston's is preferred over simple MA:**

| Condition | Indicator | Action |
|-----------|-----------|--------|
| `zero_demand_ratio >= 0.50` | ≥ 50% of days had zero demand | Use Croston's |
| `zero_demand_ratio < 0.50` | Erratic but demand most days | Use Moving Average |

**Croston's SBA derivation:**
```
demand_occasions = [qty[t] for t if qty[t] > 0]
intervals        = [t[i+1] - t[i] for consecutive demand occasions]

Initialize: z_hat = demand_occasions[0], p_hat = 1.0
For each demand occasion i:
    z_hat = alpha * demand_occasions[i] + (1 - alpha) * z_hat
    p_hat = alpha * intervals[i]         + (1 - alpha) * p_hat

SBA forecast rate = (1 - alpha/2) * (z_hat / p_hat)  units/day
```

**Minimum data for Croston's:** `>= CROSTON_MIN_OCCASIONS` (default: 3) distinct demand occasions. If fewer, fall back to Moving Average.

### 6.2 Exponential Smoothing (SES and Holt's)

**SES model equations:**
```
Level:  L_t = alpha * y_t + (1 - alpha) * L_{t-1}
Forecast: y_{t+h} = L_t   (constant for all h)
```

**Holt's Linear (Double Exponential Smoothing) equations:**
```
Level:  L_t = alpha * y_t + (1 - alpha) * (L_{t-1} + B_{t-1})
Trend:  B_t = beta  * (L_t - L_{t-1}) + (1 - beta) * B_{t-1}
Forecast: y_{t+h} = L_t + h * B_t
```

**AIC-based model selection:**
```
AIC = -2 * log(L) + 2 * k

SES:    k = 2 parameters (alpha, L_0)
Holt's: k = 3 parameters (alpha, beta, L_0, B_0) → k = 4 with initial trend

Lower AIC → preferred model (penalizes complexity)
```

**CI growth with horizon:**
```
For h-step ahead forecast:
  σ_h = σ_residual * sqrt(h)   (SES: variance grows linearly with horizon)
  CI  = forecast ± z_crit * σ_h
```

### 6.3 Holt-Winters (Triple Exponential Smoothing)

**Model equations (additive):**
```
Level:   L_t = alpha * (y_t - S_{t-m})   + (1 - alpha) * (L_{t-1} + B_{t-1})
Trend:   B_t = beta  * (L_t - L_{t-1})   + (1 - beta)  * B_{t-1}
Season:  S_t = gamma * (y_t - L_{t-1} - B_{t-1}) + (1 - gamma) * S_{t-m}
Forecast: y_{t+h} = L_t + h * B_t + S_{t+h-m(k+1)}

where m = 7 (weekly seasonal period), k = floor((h-1)/m)
```

**Confidence interval via bootstrap simulation:**
```
N_SIM = 200 simulation runs
For each simulation:
    Draw residuals with replacement from model.resid
    Propagate forward h steps using model state equations + sampled residuals
    Record simulated demand path

lower_ci[h] = percentile(simulated[:, h], (1-confidence)/2 * 100)
upper_ci[h] = percentile(simulated[:, h], (1+confidence)/2 * 100)
```

### 6.4 Accuracy Metrics: Worked Examples

**MAPE Example:**
```
Actual:   [10, 12, 0, 8, 15]  (note: day 3 has zero — excluded from MAPE)
Forecast: [11, 10, 2, 9, 13]

Errors (non-zero actuals only):
  |10-11|/10 = 10.0%
  |12-10|/12 = 16.7%
  |8-9|  /8  = 12.5%
  |15-13|/15 = 13.3%

MAPE = (10.0 + 16.7 + 12.5 + 13.3) / 4 = 13.1%
```

**RMSE Example:**
```
All 5 days used:
  errors² = [1, 4, 4, 1, 4]
  MSE     = 14 / 5 = 2.8
  RMSE    = sqrt(2.8) ≈ 1.67 units/day

Interpretation: on average, forecasts deviate by ±1.67 units/day.
This RMSE feeds into Phase 5 safety stock calculation:
  safety_stock = z * RMSE * sqrt(lead_time_days)
```

### 6.5 Portfolio MAPE Weighting

The portfolio MAPE is not a simple average — it is weighted by each product's revenue share from the ABC classification to give A-class products more influence on the headline accuracy figure:

```
portfolio_mape = SUM(mape_i * revenue_share_i for products with mape not None)
                 / SUM(revenue_share_i for products with mape not None)
```

Products without validation (C-class) are excluded from this calculation. If all products are excluded, `portfolio_mape = None`.

---

## 7. New Configuration Constants (`config/constants.py`)

| Constant | Default | Description |
|----------|---------|-------------|
| `FORECAST_HORIZON_DAYS` | 30 | Default forecast horizon in days |
| `FORECAST_HORIZON_MAX_DAYS` | 90 | Maximum allowed horizon |
| `FORECAST_CONFIDENCE_LEVEL` | 0.95 | Default confidence level for CI |
| `FORECAST_LOOKBACK_DAYS` | 90 | Training window (days of historical data used) |
| `FORECAST_MIN_TRAINING_DAYS` | 14 | Minimum data required; shorter → Moving Average fallback |
| `FORECAST_VALIDATION_DAYS` | 14 | Holdout days for A-class walk-forward validation |
| `FORECAST_VALIDATION_DAYS_B` | 7 | Holdout days for B-class (half of A) |
| `MA_WINDOW_DAYS` | 14 | Moving average look-back window |
| `CROSTON_ALPHA` | 0.1 | Smoothing parameter for Croston's SBA |
| `CROSTON_ZERO_THRESHOLD` | 0.50 | Zero-demand ratio above which Croston's is used |
| `CROSTON_MIN_OCCASIONS` | 3 | Minimum demand occasions for Croston's |
| `SEASONAL_PERIODS` | 7 | Weekly seasonality period for Holt-Winters |
| `HW_MIN_DATA_MULTIPLIER` | 3 | Holt-Winters requires >= 3 × seasonal_periods days |
| `N_SIM_BOOTSTRAP` | 200 | Monte Carlo simulation runs for Holt-Winters CI |
| `FORECAST_MAPE_EXCELLENT` | 10.0 | MAPE ≤ 10% → green |
| `FORECAST_MAPE_ACCEPTABLE` | 20.0 | MAPE ≤ 20% → amber; above → red |
| `ADEQUACY_WARNING_DAYS` | 7 | Coverage < 7 days → WARNING |
| `ADEQUACY_CRITICAL_DAYS` | 14 | Coverage < 14 days → OK threshold |
| `ADEQUACY_EXCESS_DAYS` | 90 | Coverage > 90 days → EXCESS |

---

## 8. Technology Stack (Phase 4 Additions)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Time-series models | statsmodels | >= 0.14.0 | ExponentialSmoothing (SES, Holt's, Holt-Winters) |
| Statistical distributions | scipy | >= 1.10.0 | t-distribution CI for MA; normal CI for SES |
| Array operations | numpy | >= 1.24.0 | Bootstrap simulation, CI percentiles (already declared) |

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

# Phase 4 - Demand Forecasting
statsmodels>=0.14.0
scipy>=1.10.0

# Testing
pytest>=8.0.0
pytest-cov>=4.0.0

# Development (optional)
black>=23.0.0
isort>=5.12.0
mypy>=1.0.0
```

> **Note on scipy:** Likely already installed as a transitive dependency of statsmodels. Declaring it explicitly pins the minimum version and makes the dependency explicit.

---

## 9. Implementation Tasks

### 9.1 Database Extension (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 1 | Add `ForecastRun` and `DemandForecast` ORM models + indexes | `src/database/models.py` | 1.5 hours |
| 2 | Extend `Product` model with `forecasts` relationship | `src/database/models.py` | 15 min |
| 3 | Verify schema migration: new tables created by `create_tables()` | `src/database/connection.py` | 15 min |

### 9.2 Forecasting Engine (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 4 | Create `src/forecasting/` package + `ForecastOutput` dataclass | `src/forecasting/__init__.py` | 30 min |
| 5 | Implement `BaseForecastModel` abstract class | `src/forecasting/base_model.py` | 1 hour |
| 6 | Implement `MovingAverageModel` + `CrostonModel` | `src/forecasting/moving_average.py` | 3-4 hours |
| 7 | Implement `ExponentialSmoothingModel` (SES + Holt's with AIC) | `src/forecasting/exponential_smoothing.py` | 3-4 hours |
| 8 | Implement `HoltWintersModel` (with bootstrap CI) | `src/forecasting/holt_winters.py` | 4-5 hours |
| 9 | Implement `ModelSelector` (decision tree + fallback logic) | `src/forecasting/model_selector.py` | 2-3 hours |
| 10 | Implement `AccuracyEvaluator` (walk-forward + all metrics) | `src/forecasting/accuracy_evaluator.py` | 3-4 hours |
| 11 | Implement `ForecastRunner` (orchestrator + persistence) | `src/forecasting/forecast_runner.py` | 4-5 hours |
| 12 | Add Phase 4 constants to configuration | `config/constants.py` | 30 min |

### 9.3 Service Layer (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 13 | Implement `ForecastService` (full query layer) | `src/services/forecast_service.py` | 2-3 hours |
| 14 | Add `get_daily_demand_series()` to `SalesService` | `src/services/sales_service.py` | 1 hour |
| 15 | Extend `KPIService` with `get_forecast_kpis()` | `src/services/kpi_service.py` | 1 hour |

### 9.4 UI Extensions (Priority: Medium)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 16 | Add forecast color constants to theme | `src/ui/theme.py` | 15 min |
| 17 | Implement `ForecastChart` widget (actuals + forecast + CI) | `src/ui/components/forecast_chart.py` | 3-4 hours |
| 18 | Add `plot_forecast()` to `ChartPanel` | `src/ui/components/chart_panel.py` | 1-2 hours |
| 19 | Extend `FilterBar` with horizon + confidence controls | `src/ui/components/filter_bar.py` | 1 hour |
| 20 | Implement `ForecastView` (4 sections, background thread) | `src/ui/views/forecast_view.py` | 7-8 hours |
| 21 | Add Forecast Accuracy panel to `AnalyticsView` | `src/ui/views/analytics_view.py` | 2-3 hours |
| 22 | Add Forecast nav button to main app | `src/ui/app.py` | 30 min |

### 9.5 Testing (Priority: High)

| # | Task | Module | Effort |
|---|------|--------|--------|
| 23 | Moving Average + Croston's tests | `tests/test_moving_average.py` | 3-4 hours |
| 24 | Exponential Smoothing (SES + Holt's) tests | `tests/test_exponential_smoothing.py` | 3-4 hours |
| 25 | Holt-Winters model tests | `tests/test_holt_winters.py` | 3-4 hours |
| 26 | Model Selector decision-tree tests | `tests/test_model_selector.py` | 2-3 hours |
| 27 | Accuracy Evaluator tests (MAPE, MAE, RMSE, walk-forward) | `tests/test_accuracy_evaluator.py` | 3-4 hours |
| 28 | Forecast Service integration tests | `tests/test_forecast_service.py` | 2-3 hours |

**Total estimated effort: ~60-80 hours**

---

## 10. Implementation Order

The recommended build sequence verifies each model independently before integration with the runner and UI:

```
Step 1: Database Extension
  ├── Task 1: ForecastRun + DemandForecast models
  ├── Task 2: Product.forecasts relationship
  └── Task 3: Schema migration verification

Step 2: Forecasting Engine Foundation
  ├── Task 4:  Package + ForecastOutput dataclass
  ├── Task 5:  BaseForecastModel abstract class
  └── Task 12: Constants

Step 3: Model Implementations (independent; verify each immediately)
  ├── Task 6:  MovingAverageModel + CrostonModel
  ├── Task 23: MA + Croston tests          ← verify immediately
  ├── Task 7:  ExponentialSmoothingModel
  ├── Task 24: SES + Holt's tests          ← verify immediately
  ├── Task 8:  HoltWintersModel
  └── Task 25: Holt-Winters tests          ← verify immediately

Step 4: Selection + Accuracy
  ├── Task 9:  ModelSelector
  ├── Task 26: ModelSelector tests         ← verify immediately
  ├── Task 10: AccuracyEvaluator
  └── Task 27: AccuracyEvaluator tests     ← verify immediately

Step 5: Service Layer
  ├── Task 14: SalesService.get_daily_demand_series()
  ├── Task 11: ForecastRunner (uses all models)
  ├── Task 13: ForecastService
  ├── Task 15: KPIService extension
  └── Task 28: ForecastService integration tests

Step 6: UI
  ├── Task 16: Theme extensions
  ├── Task 17: ForecastChart widget
  ├── Task 18: ChartPanel.plot_forecast()
  ├── Task 19: FilterBar extensions
  ├── Task 20: ForecastView
  ├── Task 21: AnalyticsView accuracy panel
  └── Task 22: App nav entry
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| statsmodels fitting fails on short or degenerate series (all-zeros, constant demand) | High | High | `try/except` wraps every `.fit()` call; failure → fall back to `MovingAverageModel`; log warning |
| Holt-Winters bootstrap CI computation slow for 20+ products | Medium | Medium | Run `N_SIM=200` (not 1000); parallelise with `concurrent.futures.ThreadPoolExecutor` if > 50 products |
| Negative predicted_qty from model extrapolation | Medium | Medium | All `predicted_qty` and `lower_ci` values clipped to `>= 0` in `ForecastOutput` constructor |
| MAPE undefined when all actual values are zero in holdout window | High | Medium | Return `None` for MAPE; use sMAPE and MAE as alternatives; log "zero-demand holdout" warning |
| Seasonal period of 7 wrong for products sold weekly (not daily) | Medium | Low | Seasonal period configurable per-product in future; for now, `SEASONAL_PERIODS=7` with fallback if data < 3 cycles |
| Long forecast run (28 tasks) blocks UI thread | High | Certain | Background `threading.Thread` with `after(0, callback)` (same pattern as Phase 3 classification) |
| Products classified AZ (high-value, erratic) get inaccurate forecasts | High | High | Flag AZ products explicitly in `ForecastReport.warnings`; display caution note in UI for these rows |
| Forecast run on empty `product_classifications` table (no Phase 3 run yet) | High | Low | Guard in `ForecastRunner.run()`: if no classifications exist, raise `ClassificationRequiredError` with clear message; UI shows "Run Analytics first" prompt |
| statsmodels convergence warnings pollute application logs | Low | High | Suppress with `warnings.filterwarnings("ignore", module="statsmodels")` inside model fit; log custom message instead |

---

## 12. Testing Strategy

### 12.1 Moving Average + Croston Tests (`tests/test_moving_average.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_ma_constant_demand` | [10]*14 | predicted_qty all 10; CI has zero width |
| `test_ma_varied_demand` | [5,15,8,12,6,14,10,9,11,7,13,8,10,6] | predicted_qty ≈ mean; CI uses t-dist |
| `test_ma_window_larger_than_series` | 5-day series, window=14 | Falls back to all available data |
| `test_ma_negative_clip` | Low mean, wide CI (negatives possible) | lower_ci clipped to 0 |
| `test_ma_forecast_length` | horizon=30 | `len(predicted_qty) == 30` |
| `test_croston_zero_ratio` | [0,0,5,0,0,0,8,0,0,0] | `zero_demand_ratio = 0.80 ≥ 0.50 → CrostonModel` |
| `test_croston_sba_rate` | Controlled occasions + intervals | SBA rate = (1-alpha/2) * (z_hat/p_hat) verified |
| `test_croston_insufficient_occasions` | Only 2 demand occasions | Falls back to MovingAverageModel |
| `test_forecast_output_contract` | Any model | `forecast_dates` aligned with `predicted_qty`; all ≥ 0 |

### 12.2 Exponential Smoothing Tests (`tests/test_exponential_smoothing.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_ses_level_stationary` | [10]*30 + small noise | SES selected over Holt's (lower AIC) |
| `test_holts_trending_demand` | Linear ramp [1..30] | Holt's Linear selected; forecast continues trend |
| `test_aic_selection_ses_preferred` | Flat data | SES AIC < Holt's AIC |
| `test_aic_selection_holts_preferred` | Strongly trending data | Holt's AIC < SES AIC |
| `test_ci_grows_with_horizon` | Any stable series | `upper_ci[29] > upper_ci[0]` |
| `test_ses_min_data_fallback` | 10-day series (< 14) | Returns `MovingAverageModel` output |
| `test_ses_all_zeros` | [0]*30 | statsmodels exception caught; falls back to MA |
| `test_forecast_is_non_negative` | Any series | All `predicted_qty >= 0`, all `lower_ci >= 0` |

### 12.3 Holt-Winters Tests (`tests/test_holt_winters.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_hw_weekly_seasonality` | Synthetic 7-day cycle (30 days) | Seasonal factors sum to ~0; forecast reproduces cycle |
| `test_hw_insufficient_data_fallback` | 13 days (< 3 × 7 = 21) | Falls back to `ExponentialSmoothingModel` |
| `test_hw_ci_via_bootstrap` | Known stable series | `lower_ci < predicted_qty < upper_ci` for all h |
| `test_hw_seasonal_factors_length` | 30-day series | `len(get_seasonal_factors()) == 7` |
| `test_hw_trending_seasonal` | Trend + weekly cycle | Forecast shows both trend and seasonal variation |
| `test_hw_all_zeros_fallback` | [0]*30 | Exception caught; falls back to MovingAverageModel |
| `test_hw_forecast_dates` | horizon=14 | `forecast_dates[0] == today + 1 day` |

### 12.4 Model Selector Tests (`tests/test_model_selector.py`)

| Test | Classification | Data | Expected Model |
|------|---------------|------|---------------|
| `test_select_x_class` | XYZ=X | 30-day stable | ExponentialSmoothingModel |
| `test_select_y_class_enough_data` | XYZ=Y | 30-day | HoltWintersModel |
| `test_select_y_class_short_data` | XYZ=Y | 10-day | ExponentialSmoothingModel (fallback) |
| `test_select_z_intermittent` | XYZ=Z, zero_ratio=0.70 | Any | CrostonModel |
| `test_select_z_erratic_not_intermittent` | XYZ=Z, zero_ratio=0.30 | Any | MovingAverageModel |
| `test_select_insufficient_data` | Any | 7-day | MovingAverageModel (data fallback) |
| `test_validation_days_a_class` | ABC=A | Any | `get_validation_days("A") == 14` |
| `test_validation_days_b_class` | ABC=B | Any | `get_validation_days("B") == 7` |
| `test_validation_days_c_class` | ABC=C | Any | `get_validation_days("C") == 0` |

### 12.5 Accuracy Evaluator Tests (`tests/test_accuracy_evaluator.py`)

| Test | Input | Expected |
|------|-------|----------|
| `test_mape_perfect_forecast` | actual=[10,10,10], forecast=[10,10,10] | MAPE=0.0% |
| `test_mape_excludes_zeros` | actual=[10,0,12], forecast=[11,2,10] | MAPE uses days 1 and 3 only |
| `test_mape_all_zeros_returns_none` | actual=[0,0,0] | MAPE=None |
| `test_mae_computation` | actual=[10,12], forecast=[11,10] | MAE=(1+2)/2=1.5 |
| `test_rmse_computation` | actual=[10,12], forecast=[11,10] | RMSE=sqrt((1+4)/2)≈1.58 |
| `test_smape_symmetry` | Swap actual/forecast | sMAPE is unchanged (symmetric) |
| `test_walk_forward_holdout_size` | series=30 days, validation=7 | Train on 23, test on 7 |
| `test_walk_forward_returns_accuracy_result` | Known series | `AccuracyResult` structure correct |

### 12.6 Forecast Service Tests (`tests/test_forecast_service.py`)

End-to-end integration tests using seeded database:

| Test | Scenario |
|------|----------|
| `test_run_forecast_persists` | After run, `forecast_runs` has 1 row; `demand_forecasts` has 20×30=600 rows |
| `test_get_latest_forecast` | Returns correct dates and quantities from most recent run |
| `test_get_accuracy_table` | Returns one dict per product; MAPE is None for C-class |
| `test_multiple_runs_latest_used` | Two runs; `get_latest_forecast()` returns data from run 2 |
| `test_no_forecast_state` | Empty DB returns `[]` or `None` without exception |
| `test_portfolio_mape_weighted` | Known MAPE per product + known revenue shares → verify weighted result |
| `test_run_without_classification_raises` | No Phase 3 run → `ClassificationRequiredError` raised |

---

## 13. Non-Functional Requirements (Phase 4)

| Requirement | Target | Validation Method |
|-------------|--------|-------------------|
| Full portfolio forecast run time | < 30 seconds for 20 products | Profile with sample dataset; each product ~1.5s |
| Full portfolio forecast run time (1,000 products) | < 5 minutes | Extrapolation from 20-product benchmark |
| Single-product re-forecast time | < 3 seconds | Manual test via "Refresh" button |
| Forecast chart render time | < 1 second | Matplotlib timing |
| MAPE target (X-class products) | < 15% | Validation on sample dataset |
| MAPE target (Y-class products) | < 25% | Validation on sample dataset |
| Forecast persistence size | < 5 MB for 20 products × 90 days | SQLite file size check |
| Memory during bootstrap simulation | < 50 MB additional | `tracemalloc` profiling |
| Thread safety | No UI freeze during forecast run | Manual testing |
| Graceful failure | No crash on degenerate series | Fuzz testing with edge-case inputs |

---

## 14. Phase 4 Exit Criteria

- [ ] `forecast_runs` and `demand_forecasts` tables created; schema migration verified
- [ ] `MovingAverageModel` produces correct point forecast and CI (test: `test_ma_constant_demand`)
- [ ] `CrostonModel` applies SBA formula correctly; falls back when occasions < minimum (all MA/Croston tests pass)
- [ ] `ExponentialSmoothingModel` selects SES vs. Holt's by AIC; CI grows with horizon (all SES tests pass)
- [ ] `HoltWintersModel` produces seasonally adjusted forecast with bootstrap CI; falls back when data < 3 cycles (all HW tests pass)
- [ ] `ModelSelector` routes every ABC-XYZ combination to the correct model class (all selector tests pass)
- [ ] `AccuracyEvaluator` computes MAPE (skipping zeros), MAE, RMSE correctly; walk-forward holdout sized by ABC class (all evaluator tests pass)
- [ ] `ForecastRunner.run()` completes for all 20 sample products; persists 600 rows in `demand_forecasts`
- [ ] `ForecastService.get_latest_forecast()` returns correct per-product forecast from most recent run
- [ ] `ForecastService.run_forecast()` raises `ClassificationRequiredError` when no Phase 3 data exists
- [ ] Forecast View renders all 4 sections (summary cards, accuracy table, forecast chart, adequacy table)
- [ ] Forecast chart correctly shows historical actuals + forecast line + CI band with "today" divider
- [ ] Row click in accuracy table updates forecast chart for the selected product
- [ ] Demand Adequacy table computes coverage days and status correctly
- [ ] Analytics View shows Forecast Accuracy panel with portfolio MAPE and bar chart by ABC class
- [ ] "Run Forecast" executes in background thread; UI remains responsive
- [ ] `ClassificationRequiredError` displays a "Run Analytics first" prompt in the UI (no crash)
- [ ] All 6 new test modules pass with 100% success
- [ ] Full 20-product forecast run completes in < 30 seconds

---

## 15. Transition to Phase 5

Phase 5 (Inventory Optimization) will consume Phase 4 outputs directly:

1. **Reorder Point (ROP) calculation** uses forecast demand during lead time:
   ```
   demand_during_lead_time = SUM(predicted_qty[0:lead_time_days])
   safety_stock            = z_score * rmse * sqrt(lead_time_days)
   reorder_point           = demand_during_lead_time + safety_stock
   ```
   `rmse` from `DemandForecast.rmse`; `lead_time_days` from `Supplier.lead_time_days`.

2. **Economic Order Quantity (EOQ)** uses annualized forecast demand:
   ```
   annual_demand = SUM(predicted_qty) * (365 / horizon_days)
   EOQ = sqrt(2 * annual_demand * ordering_cost / holding_cost_per_unit)
   ```

3. **Replenishment alerts** trigger when:
   ```
   current_stock <= reorder_point
   ```
   Phase 5 will create `ReplenishmentAlert` records for any product meeting this condition, surfaced in the Dashboard and a new Alerts View.

4. **Safety stock sizing** uses RMSE (not MAPE) as the error metric for Phase 5:
   - RMSE is in demand units — directly usable in safety stock formulas
   - MAPE (a percentage) requires additional scaling; RMSE avoids this

5. **Forecast View extended** in Phase 5 to display the computed ROP and EOQ alongside each product's forecast chart.

**Prerequisites from Phase 4:**
- `DemandForecast` table populated with `predicted_qty`, `rmse`, and `is_validated` columns
- `ForecastService.get_latest_forecast(product_id)` returning per-day predictions
- `ForecastService.get_accuracy_table()` providing `rmse` per product for safety stock formulas
- `ForecastView` Demand Adequacy table as the UI foundation for Phase 5 alerts integration

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-20 | Initial Phase 4 implementation plan |

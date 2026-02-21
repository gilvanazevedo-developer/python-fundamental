"""
Demand Forecasting Engine
Pure-function demand forecasting using Simple Moving Average (SMA),
Weighted Moving Average (WMA), and Linear Trend (OLS regression).

All functions are stateless and require no database access.
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DemandSeries:
    """Continuous daily demand series for a single product."""
    product_id: str
    product_name: str
    category: str
    dates: List[str]          # ISO-8601 date strings, one per day, oldest first
    quantities: List[int]     # Units sold; 0 for days with no recorded sale


@dataclass
class ForecastResult:
    """Output of a demand forecast computation."""
    product_id: str
    product_name: str
    category: str
    method: str               # "SMA", "WMA", or "LINEAR"
    horizon_days: int         # Number of days forecasted forward
    historical_daily_avg: float  # Mean daily demand in the lookback window
    forecast_daily: float     # Predicted average daily demand going forward
    forecast_total: int       # Total units expected over horizon_days
    std_dev: float            # Std-dev of historical daily demand
    mae: float                # Mean Absolute Error from walk-forward validation
    forecast_dates: List[str] = field(default_factory=list)  # ISO dates for forecast
    forecast_values: List[float] = field(default_factory=list)  # One per day


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_series(
    product_id: str,
    product_name: str,
    category: str,
    raw_rows: List[Dict],
    start_date: date,
    end_date: date,
) -> DemandSeries:
    """
    Build a gapless DemandSeries from sparse DB rows.

    raw_rows must contain dicts with keys ``date`` (str "YYYY-MM-DD")
    and ``total_quantity`` (int).  Missing days are filled with zero.
    """
    qty_by_date: Dict[str, int] = {
        r["date"]: int(r["total_quantity"]) for r in raw_rows
    }

    dates: List[str] = []
    quantities: List[int] = []

    current = start_date
    while current <= end_date:
        ds = current.isoformat()
        dates.append(ds)
        quantities.append(qty_by_date.get(ds, 0))
        current += timedelta(days=1)

    return DemandSeries(
        product_id=product_id,
        product_name=product_name,
        category=category,
        dates=dates,
        quantities=quantities,
    )


# ---------------------------------------------------------------------------
# Forecasting algorithms
# ---------------------------------------------------------------------------

def simple_moving_average(quantities: List[int], window: int) -> float:
    """
    Simple Moving Average — mean of the last ``window`` observations.

    Returns 0.0 if the series is empty or has fewer points than the window.
    """
    if not quantities:
        return 0.0
    subset = quantities[-window:] if len(quantities) >= window else quantities
    return statistics.mean(subset)


def weighted_moving_average(quantities: List[int], window: int) -> float:
    """
    Weighted Moving Average — linear weights, most-recent observation has
    the highest weight.

    Returns 0.0 if the series is empty.
    """
    if not quantities:
        return 0.0
    subset = quantities[-window:] if len(quantities) >= window else quantities
    n = len(subset)
    weights = list(range(1, n + 1))     # [1, 2, 3, …, n]
    total_weight = sum(weights)
    return sum(w * q for w, q in zip(weights, subset)) / total_weight


def _ols(x: List[float], y: List[float]):
    """Ordinary least-squares slope and intercept for y ~ a + b*x."""
    n = len(x)
    if n < 2:
        return 0.0, float(y[0]) if y else 0.0

    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)

    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)

    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def linear_trend_forecast(
    quantities: List[int],
    horizon_days: int,
) -> List[float]:
    """
    Linear Trend — OLS regression on the historical series.

    Returns a list of ``horizon_days`` predicted daily demand values.
    Values are clipped to >= 0 (demand cannot be negative).
    """
    if not quantities:
        return [0.0] * horizon_days

    x = list(range(len(quantities)))
    y = [float(q) for q in quantities]
    slope, intercept = _ols(x, y)

    start_idx = len(quantities)
    return [max(0.0, intercept + slope * (start_idx + i)) for i in range(horizon_days)]


def _walk_forward_mae(quantities: List[int], method: str, window: int) -> float:
    """
    Walk-forward validation: train on [0..t-1], predict t, compare to actual.
    Returns mean absolute error over the last half of the series.
    Requires at least window+1 points; returns 0 if series is too short.
    """
    if len(quantities) < window + 1:
        return 0.0

    errors = []
    half = len(quantities) // 2
    eval_start = max(window, half)

    for t in range(eval_start, len(quantities)):
        train = quantities[:t]
        actual = quantities[t]

        if method == "SMA":
            pred = simple_moving_average(train, window)
        elif method == "WMA":
            pred = weighted_moving_average(train, window)
        else:  # LINEAR
            forecasts = linear_trend_forecast(train, 1)
            pred = forecasts[0] if forecasts else 0.0

        errors.append(abs(pred - actual))

    return statistics.mean(errors) if errors else 0.0


# ---------------------------------------------------------------------------
# High-level forecast entry point
# ---------------------------------------------------------------------------

def forecast(
    series: DemandSeries,
    method: str = "SMA",
    horizon_days: int = 30,
    window: int = 14,
) -> ForecastResult:
    """
    Compute a demand forecast for ``horizon_days`` ahead.

    Args:
        series:       DemandSeries built from historical data.
        method:       One of "SMA", "WMA", "LINEAR".
        horizon_days: Number of future days to forecast.
        window:       Lookback window for SMA/WMA (ignored for LINEAR).

    Returns:
        ForecastResult with per-day forecast values and summary statistics.
    """
    qty = series.quantities
    method = method.upper()

    # Per-day forecast values
    if method == "SMA":
        daily_forecast = simple_moving_average(qty, window)
        forecast_values = [daily_forecast] * horizon_days
    elif method == "WMA":
        daily_forecast = weighted_moving_average(qty, window)
        forecast_values = [daily_forecast] * horizon_days
    else:  # LINEAR
        forecast_values = linear_trend_forecast(qty, horizon_days)
        daily_forecast = statistics.mean(forecast_values) if forecast_values else 0.0

    # Summary stats on historical series
    historical_avg = statistics.mean(qty) if qty else 0.0
    std_dev = statistics.pstdev(qty) if len(qty) >= 2 else 0.0

    # MAE via walk-forward validation
    mae = _walk_forward_mae(qty, method, window)

    # Build future date labels
    last_date = date.fromisoformat(series.dates[-1]) if series.dates else date.today()
    forecast_dates = [
        (last_date + timedelta(days=i + 1)).isoformat()
        for i in range(horizon_days)
    ]

    return ForecastResult(
        product_id=series.product_id,
        product_name=series.product_name,
        category=series.category,
        method=method,
        horizon_days=horizon_days,
        historical_daily_avg=round(historical_avg, 2),
        forecast_daily=round(daily_forecast, 2),
        forecast_total=round(sum(forecast_values)),
        std_dev=round(std_dev, 2),
        mae=round(mae, 2),
        forecast_dates=forecast_dates,
        forecast_values=[round(v, 2) for v in forecast_values],
    )

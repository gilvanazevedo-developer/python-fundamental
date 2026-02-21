"""
Unit tests for src/analytics/forecasting.py

Pure-function tests — no database required.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import math
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.forecasting import (
    build_series,
    simple_moving_average,
    weighted_moving_average,
    linear_trend_forecast,
    forecast,
    DemandSeries,
    ForecastResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def flat_series():
    """14-day series with constant demand of 10 units/day."""
    start = date(2024, 1, 1)
    end = date(2024, 1, 14)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(14)]
    quantities = [10] * 14
    return DemandSeries(
        product_id="P1", product_name="Flat", category="X",
        dates=dates, quantities=quantities
    )


@pytest.fixture
def trending_series():
    """14-day series with demand growing by 1 unit/day (1, 2, 3, …, 14)."""
    start = date(2024, 1, 1)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(14)]
    quantities = list(range(1, 15))
    return DemandSeries(
        product_id="P2", product_name="Trend", category="Y",
        dates=dates, quantities=quantities
    )


@pytest.fixture
def zero_series():
    """7-day series with zero demand."""
    start = date(2024, 1, 1)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(7)]
    return DemandSeries(
        product_id="P3", product_name="Zero", category="Z",
        dates=dates, quantities=[0] * 7
    )


# ---------------------------------------------------------------------------
# build_series
# ---------------------------------------------------------------------------

class TestBuildSeries:

    def test_gapless_output(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        # Only rows for day 1 and day 3
        raw = [{"date": "2024-01-01", "total_quantity": 5},
               {"date": "2024-01-03", "total_quantity": 8}]
        s = build_series("P1", "X", "Cat", raw, start, end)
        assert len(s.dates) == 5
        assert len(s.quantities) == 5

    def test_missing_days_filled_with_zero(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)
        raw = [{"date": "2024-01-01", "total_quantity": 10}]
        s = build_series("P1", "X", "Cat", raw, start, end)
        assert s.quantities == [10, 0, 0]

    def test_all_days_present(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)
        raw = [
            {"date": "2024-01-01", "total_quantity": 1},
            {"date": "2024-01-02", "total_quantity": 2},
            {"date": "2024-01-03", "total_quantity": 3},
        ]
        s = build_series("P1", "X", "Cat", raw, start, end)
        assert s.quantities == [1, 2, 3]

    def test_empty_raw_all_zeros(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        s = build_series("P1", "X", "Cat", [], start, end)
        assert s.quantities == [0, 0, 0, 0, 0]

    def test_dates_are_sorted(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        s = build_series("P1", "X", "Cat", [], start, end)
        assert s.dates == sorted(s.dates)

    def test_fields_populated(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 1)
        s = build_series("P99", "My Product", "Gadgets", [], start, end)
        assert s.product_id == "P99"
        assert s.product_name == "My Product"
        assert s.category == "Gadgets"


# ---------------------------------------------------------------------------
# simple_moving_average
# ---------------------------------------------------------------------------

class TestSMA:

    def test_constant_series(self):
        assert simple_moving_average([10, 10, 10, 10], window=3) == pytest.approx(10.0)

    def test_window_larger_than_series(self):
        # Uses all available points when window > len
        assert simple_moving_average([5, 10], window=7) == pytest.approx(7.5)

    def test_window_subset(self):
        # SMA of last 2 from [1, 2, 3, 4, 5] = (4+5)/2 = 4.5
        assert simple_moving_average([1, 2, 3, 4, 5], window=2) == pytest.approx(4.5)

    def test_empty_returns_zero(self):
        assert simple_moving_average([], window=5) == 0.0

    def test_single_element(self):
        assert simple_moving_average([7], window=3) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# weighted_moving_average
# ---------------------------------------------------------------------------

class TestWMA:

    def test_constant_series_equals_constant(self):
        # Weighted average of equal values = that value
        assert weighted_moving_average([5, 5, 5], window=3) == pytest.approx(5.0)

    def test_weights_favour_recent(self):
        # Series [1, 2, 3], window=3 → weights [1,2,3], total=6
        # WMA = (1*1 + 2*2 + 3*3) / 6 = 14/6 ≈ 2.333
        result = weighted_moving_average([1, 2, 3], window=3)
        assert result == pytest.approx(14 / 6, abs=0.01)

    def test_empty_returns_zero(self):
        assert weighted_moving_average([], window=5) == 0.0

    def test_window_larger_than_series(self):
        # Uses all available; [2, 4] with weights [1,2] → (2+8)/3 ≈ 3.333
        result = weighted_moving_average([2, 4], window=10)
        assert result == pytest.approx(10 / 3, abs=0.01)

    def test_wma_greater_than_sma_for_growing_series(self):
        # For an increasing series, WMA > SMA because recent (higher) values get more weight
        series = [1, 2, 3, 4, 5]
        sma = simple_moving_average(series, window=5)
        wma = weighted_moving_average(series, window=5)
        assert wma > sma


# ---------------------------------------------------------------------------
# linear_trend_forecast
# ---------------------------------------------------------------------------

class TestLinearTrend:

    def test_flat_series_predicts_same_value(self):
        # Constant series → zero slope → forecast = constant
        series = [5] * 10
        forecast_vals = linear_trend_forecast(series, horizon_days=3)
        for v in forecast_vals:
            assert v == pytest.approx(5.0, abs=0.5)

    def test_perfect_trend(self):
        # Series [1,2,3,4,5] → slope=1, intercept=1
        # Next 3 days: 6, 7, 8
        series = list(range(1, 6))
        forecast_vals = linear_trend_forecast(series, horizon_days=3)
        assert len(forecast_vals) == 3
        assert forecast_vals[0] == pytest.approx(6.0, abs=0.1)
        assert forecast_vals[1] == pytest.approx(7.0, abs=0.1)
        assert forecast_vals[2] == pytest.approx(8.0, abs=0.1)

    def test_returns_correct_length(self):
        series = [3, 5, 7]
        result = linear_trend_forecast(series, horizon_days=10)
        assert len(result) == 10

    def test_empty_series_returns_zeros(self):
        result = linear_trend_forecast([], horizon_days=5)
        assert result == [0.0] * 5

    def test_forecast_values_non_negative(self):
        # Declining series; output should be clipped at 0
        series = [10, 8, 6, 4, 2]
        result = linear_trend_forecast(series, horizon_days=20)
        assert all(v >= 0 for v in result)

    def test_single_element(self):
        # Single point → slope=0 → constant forecast
        result = linear_trend_forecast([7], horizon_days=3)
        assert all(v == pytest.approx(7.0, abs=0.01) for v in result)


# ---------------------------------------------------------------------------
# forecast() — integration of the full pipeline
# ---------------------------------------------------------------------------

class TestForecast:

    def test_returns_forecast_result(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=7, window=7)
        assert isinstance(result, ForecastResult)

    def test_sma_on_flat_series(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=7, window=7)
        assert result.forecast_daily == pytest.approx(10.0, abs=0.1)
        assert result.forecast_total == 70

    def test_wma_on_flat_series(self, flat_series):
        result = forecast(flat_series, method="WMA", horizon_days=7, window=7)
        assert result.forecast_daily == pytest.approx(10.0, abs=0.1)

    def test_linear_on_trending_series(self, trending_series):
        result = forecast(trending_series, method="LINEAR", horizon_days=3)
        # Series 1..14, next values should be near 15, 16, 17
        assert result.forecast_values[0] == pytest.approx(15.0, abs=1.0)

    def test_zero_demand_gives_zero_forecast(self, zero_series):
        result = forecast(zero_series, method="SMA", horizon_days=7, window=7)
        assert result.forecast_daily == 0.0
        assert result.forecast_total == 0

    def test_forecast_dates_length(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=14)
        assert len(result.forecast_dates) == 14
        assert len(result.forecast_values) == 14

    def test_forecast_dates_after_history(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=5)
        # All forecast dates must come after the last historical date
        last_hist = flat_series.dates[-1]
        for fd in result.forecast_dates:
            assert fd > last_hist

    def test_method_stored_uppercase(self, flat_series):
        result = forecast(flat_series, method="sma", horizon_days=5)
        assert result.method == "SMA"

    def test_mae_non_negative(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=7, window=5)
        assert result.mae >= 0

    def test_std_dev_zero_for_flat_series(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=7)
        assert result.std_dev == pytest.approx(0.0, abs=0.01)

    def test_historical_avg_matches_series(self, flat_series):
        result = forecast(flat_series, method="SMA", horizon_days=7)
        assert result.historical_daily_avg == pytest.approx(10.0)

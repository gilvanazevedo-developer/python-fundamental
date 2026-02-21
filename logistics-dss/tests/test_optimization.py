"""
Unit tests for src/analytics/optimization.py

Pure-function tests — no database required.
"""

import sys
import math
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.optimization import (
    eoq,
    total_inventory_cost,
    safety_stock,
    reorder_point,
    optimize,
    OptimizationResult,
)


# ---------------------------------------------------------------------------
# eoq()
# ---------------------------------------------------------------------------

class TestEOQ:

    def test_classic_formula(self):
        # Q* = sqrt(2 * 1000 * 50 / 5) = sqrt(20000) ≈ 141.42
        result = eoq(annual_demand=1000, ordering_cost=50, holding_cost_per_unit=5)
        assert result == pytest.approx(math.sqrt(20000), abs=0.01)

    def test_zero_demand_returns_zero(self):
        assert eoq(0, 50, 5) == 0.0

    def test_zero_ordering_cost_returns_zero(self):
        assert eoq(1000, 0, 5) == 0.0

    def test_zero_holding_cost_returns_zero(self):
        assert eoq(1000, 50, 0) == 0.0

    def test_negative_demand_returns_zero(self):
        assert eoq(-100, 50, 5) == 0.0

    def test_higher_ordering_cost_increases_eoq(self):
        # Higher S → bigger batches (fewer orders)
        q_low = eoq(1000, 10, 5)
        q_high = eoq(1000, 100, 5)
        assert q_high > q_low

    def test_higher_holding_cost_decreases_eoq(self):
        # Higher H → smaller batches (lower stock)
        q_low_h = eoq(1000, 50, 2)
        q_high_h = eoq(1000, 50, 10)
        assert q_high_h < q_low_h

    def test_square_root_relationship(self):
        # Doubling demand increases EOQ by √2
        q1 = eoq(1000, 50, 5)
        q2 = eoq(2000, 50, 5)
        assert q2 == pytest.approx(q1 * math.sqrt(2), abs=0.1)


# ---------------------------------------------------------------------------
# total_inventory_cost()
# ---------------------------------------------------------------------------

class TestTotalInventoryCost:

    def test_returns_dict_with_expected_keys(self):
        result = total_inventory_cost(1000, 100, 50, 5)
        assert set(result.keys()) == {"annual_holding", "annual_ordering", "total"}

    def test_holding_cost_calculation(self):
        # (Q/2) × H = (100/2) × 5 = 250
        result = total_inventory_cost(1000, 100, 50, 5)
        assert result["annual_holding"] == pytest.approx(250.0)

    def test_ordering_cost_calculation(self):
        # (D/Q) × S = (1000/100) × 50 = 500
        result = total_inventory_cost(1000, 100, 50, 5)
        assert result["annual_ordering"] == pytest.approx(500.0)

    def test_total_is_sum(self):
        result = total_inventory_cost(1000, 100, 50, 5)
        assert result["total"] == pytest.approx(
            result["annual_holding"] + result["annual_ordering"]
        )

    def test_zero_order_qty_returns_zeros(self):
        result = total_inventory_cost(1000, 0, 50, 5)
        assert result["total"] == 0.0

    def test_cost_minimised_at_eoq(self):
        D, S, H = 1000, 50, 5
        q_star = eoq(D, S, H)
        cost_at_eoq = total_inventory_cost(D, q_star, S, H)["total"]
        # Any deviation from EOQ should increase cost
        cost_at_half = total_inventory_cost(D, q_star * 0.5, S, H)["total"]
        cost_at_double = total_inventory_cost(D, q_star * 2, S, H)["total"]
        assert cost_at_eoq <= cost_at_half + 0.01
        assert cost_at_eoq <= cost_at_double + 0.01

    def test_at_eoq_holding_equals_ordering(self):
        # A fundamental property: at EOQ, holding cost = ordering cost
        D, S, H = 500, 40, 8
        q_star = eoq(D, S, H)
        result = total_inventory_cost(D, q_star, S, H)
        assert result["annual_holding"] == pytest.approx(result["annual_ordering"], rel=0.01)


# ---------------------------------------------------------------------------
# safety_stock()
# ---------------------------------------------------------------------------

class TestSafetyStock:

    def test_basic_calculation(self):
        # SS = 1.65 × 3 × √7 ≈ 1.65 × 3 × 2.6458 ≈ 13.09
        result = safety_stock(std_dev_daily=3, lead_time_days=7, service_level_z=1.65)
        assert result == pytest.approx(1.65 * 3 * math.sqrt(7), abs=0.01)

    def test_zero_std_dev_returns_zero(self):
        assert safety_stock(0, 7, 1.65) == 0.0

    def test_zero_lead_time_returns_zero(self):
        assert safety_stock(3, 0, 1.65) == 0.0

    def test_higher_z_increases_safety_stock(self):
        ss_90 = safety_stock(3, 7, 1.28)
        ss_99 = safety_stock(3, 7, 2.33)
        assert ss_99 > ss_90

    def test_higher_std_dev_increases_safety_stock(self):
        ss_low = safety_stock(1, 7, 1.65)
        ss_high = safety_stock(5, 7, 1.65)
        assert ss_high > ss_low

    def test_result_non_negative(self):
        assert safety_stock(2, 5, 1.65) >= 0


# ---------------------------------------------------------------------------
# reorder_point()
# ---------------------------------------------------------------------------

class TestReorderPoint:

    def test_basic_calculation(self):
        # ROP = 10 × 7 + 20 = 90
        result = reorder_point(daily_demand=10, lead_time_days=7, safety_stk=20)
        assert result == pytest.approx(90.0)

    def test_zero_demand_returns_safety_stock(self):
        result = reorder_point(daily_demand=0, lead_time_days=7, safety_stk=15)
        assert result == pytest.approx(15.0)

    def test_zero_safety_stock(self):
        result = reorder_point(daily_demand=5, lead_time_days=3, safety_stk=0)
        assert result == pytest.approx(15.0)

    def test_result_non_negative(self):
        assert reorder_point(-1, 7, 0) >= 0


# ---------------------------------------------------------------------------
# optimize()
# ---------------------------------------------------------------------------

class TestOptimize:

    @pytest.fixture
    def standard_inputs(self):
        return dict(
            product_id="P1", product_name="Widget", category="Widgets",
            daily_demand=10.0, std_dev_daily=2.0,
            unit_cost=20.0, carrying_cost_rate=0.25,
            ordering_cost=50.0, lead_time_days=7,
            current_stock=100, service_level_z=1.65,
        )

    def test_returns_optimization_result(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert isinstance(result, OptimizationResult)

    def test_zero_demand_returns_none(self, standard_inputs):
        standard_inputs["daily_demand"] = 0
        assert optimize(**standard_inputs) is None

    def test_zero_unit_cost_returns_none(self, standard_inputs):
        standard_inputs["unit_cost"] = 0
        assert optimize(**standard_inputs) is None

    def test_eoq_positive(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert result.eoq > 0

    def test_safety_stock_non_negative(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert result.safety_stock >= 0

    def test_reorder_point_non_negative(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert result.reorder_point >= 0

    def test_eoq_total_cost_less_than_current(self, standard_inputs):
        # When current stock differs from EOQ, potential savings should be ≥ 0
        result = optimize(**standard_inputs)
        assert result.potential_savings >= 0

    def test_orders_per_year_positive(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert result.orders_per_year > 0

    def test_annual_demand_matches_inputs(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert result.annual_demand == pytest.approx(10.0 * 365, abs=0.1)

    def test_savings_pct_between_0_and_100(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert 0 <= result.savings_pct <= 100

    def test_current_order_qty_uses_stock(self, standard_inputs):
        standard_inputs["current_stock"] = 250
        result = optimize(**standard_inputs)
        assert result.current_order_qty == pytest.approx(250, abs=1)

    def test_eoq_cost_equals_holding_plus_ordering(self, standard_inputs):
        result = optimize(**standard_inputs)
        assert result.eoq_total_cost == pytest.approx(
            result.eoq_annual_holding + result.eoq_annual_ordering, abs=0.01
        )

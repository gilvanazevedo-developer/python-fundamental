"""
Unit tests for src/analytics/abc_analysis.py

Pure-function tests — no database required.
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.abc_analysis import classify, summarize, ABCItem, ABCSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def five_products():
    """Five products whose revenues create predictable ABC buckets.

    Total revenue = 1000 — revenues chosen to keep cumulative percentages
    well away from the 70 % and 90 % thresholds (avoids float rounding edge cases).

    P1  800  80 %   starts at  0 % → A  (0 % < 70 %)
    P2  120  12 %   starts at 80 % → B  (80 % ≥ 70 %, 80 % < 90 %)
    P3   40   4 %   starts at 92 % → C  (92 % ≥ 90 %)
    P4   25   2.5%  starts at 96 % → C
    P5   15   1.5%  starts at 98.5% → C
    """
    return [
        {"product_id": "P1", "product_name": "Alpha",   "category": "X", "total_revenue": 800, "total_quantity": 80},
        {"product_id": "P2", "product_name": "Beta",    "category": "X", "total_revenue": 120, "total_quantity": 12},
        {"product_id": "P3", "product_name": "Gamma",   "category": "Y", "total_revenue":  40, "total_quantity":  4},
        {"product_id": "P4", "product_name": "Delta",   "category": "Y", "total_revenue":  25, "total_quantity":  3},
        {"product_id": "P5", "product_name": "Epsilon", "category": "Y", "total_revenue":  15, "total_quantity":  2},
    ]


# ---------------------------------------------------------------------------
# classify() — basic correctness
# ---------------------------------------------------------------------------

class TestClassify:

    def test_returns_list_of_abc_items(self, five_products):
        result = classify(five_products)
        assert isinstance(result, list)
        assert all(isinstance(i, ABCItem) for i in result)

    def test_sorted_descending_by_revenue(self, five_products):
        result = classify(five_products)
        revenues = [i.total_revenue for i in result]
        assert revenues == sorted(revenues, reverse=True)

    def test_correct_abc_classes(self, five_products):
        result = classify(five_products)
        classes = {i.product_id: i.abc_class for i in result}
        assert classes["P1"] == "A"
        assert classes["P2"] == "B"
        assert classes["P3"] == "C"
        assert classes["P4"] == "C"
        assert classes["P5"] == "C"

    def test_revenue_pct_sums_to_100(self, five_products):
        result = classify(five_products)
        total = sum(i.revenue_pct for i in result)
        assert abs(total - 100.0) < 0.1

    def test_cumulative_pct_last_item_is_100(self, five_products):
        result = classify(five_products)
        assert abs(result[-1].cumulative_pct - 100.0) < 0.1

    def test_cumulative_pct_monotonically_increasing(self, five_products):
        result = classify(five_products)
        for i in range(1, len(result)):
            assert result[i].cumulative_pct >= result[i - 1].cumulative_pct

    def test_fields_populated_correctly(self, five_products):
        result = classify(five_products)
        p1 = next(i for i in result if i.product_id == "P1")
        assert p1.product_name == "Alpha"
        assert p1.category == "X"
        assert p1.total_revenue == 800.0
        assert p1.total_quantity == 80
        assert p1.revenue_pct == pytest.approx(80.0, abs=0.1)


# ---------------------------------------------------------------------------
# classify() — edge cases
# ---------------------------------------------------------------------------

class TestClassifyEdgeCases:

    def test_empty_input_returns_empty(self):
        assert classify([]) == []

    def test_all_zero_revenue_returns_empty(self):
        products = [
            {"product_id": "P1", "product_name": "A", "total_revenue": 0},
            {"product_id": "P2", "product_name": "B", "total_revenue": 0},
        ]
        assert classify(products) == []

    def test_zero_revenue_products_excluded(self, five_products):
        five_products.append(
            {"product_id": "P6", "product_name": "Zero", "total_revenue": 0}
        )
        result = classify(five_products)
        ids = [i.product_id for i in result]
        assert "P6" not in ids
        assert len(result) == 5

    def test_single_product_is_class_a(self):
        products = [{"product_id": "P1", "product_name": "Solo", "total_revenue": 100}]
        result = classify(products)
        assert len(result) == 1
        assert result[0].abc_class == "A"

    def test_optional_fields_default_correctly(self):
        products = [{"product_id": "P1", "product_name": "Bare", "total_revenue": 100}]
        item = classify(products)[0]
        assert item.category == ""
        assert item.total_quantity == 0

    def test_custom_thresholds(self, five_products):
        # With A=50%, B=85%:
        # P1 (80 %) → A  (starts at  0 % < 50 %)
        # P2 (12 %) → B  (starts at 80 % ≥ 50 %, 80 % < 85 %)
        # P3 ( 4 %) → C  (starts at 92 % ≥ 85 %)
        # P4 ( 2.5%) → C
        # P5 ( 1.5%) → C
        result = classify(five_products, a_threshold=0.50, b_threshold=0.85)
        classes = {i.product_id: i.abc_class for i in result}
        assert classes["P1"] == "A"
        assert classes["P2"] == "B"
        assert classes["P3"] == "C"
        assert classes["P4"] == "C"
        assert classes["P5"] == "C"

    def test_revenue_rounded_to_2_decimals(self):
        products = [{"product_id": "P1", "product_name": "X", "total_revenue": 1.2345}]
        result = classify(products)
        assert result[0].total_revenue == round(1.2345, 2)


# ---------------------------------------------------------------------------
# summarize()
# ---------------------------------------------------------------------------

class TestSummarize:

    def test_returns_three_summaries(self, five_products):
        items = classify(five_products)
        summaries = summarize(items)
        assert len(summaries) == 3
        assert [s.abc_class for s in summaries] == ["A", "B", "C"]

    def test_summary_product_counts(self, five_products):
        items = classify(five_products)
        summaries = {s.abc_class: s for s in summarize(items)}
        assert summaries["A"].product_count == 1
        assert summaries["B"].product_count == 1
        assert summaries["C"].product_count == 3

    def test_summary_revenue_pct_sums_to_100(self, five_products):
        items = classify(five_products)
        summaries = summarize(items)
        total = sum(s.revenue_pct for s in summaries)
        assert abs(total - 100.0) < 0.5  # allow rounding

    def test_summary_product_pct_sums_to_100(self, five_products):
        items = classify(five_products)
        summaries = summarize(items)
        total = sum(s.product_pct for s in summaries)
        assert abs(total - 100.0) < 0.5

    def test_empty_items_returns_zero_summaries(self):
        summaries = summarize([])
        assert len(summaries) == 3
        for s in summaries:
            assert s.product_count == 0
            assert s.total_revenue == 0.0
            assert s.revenue_pct == 0.0
            assert s.product_pct == 0.0

    def test_class_a_revenue_near_threshold(self, five_products):
        items = classify(five_products)
        summaries = {s.abc_class: s for s in summarize(items)}
        # A holds only P1 = 800 of 1000 = 80 %
        assert summaries["A"].revenue_pct == pytest.approx(80.0, abs=0.5)

    def test_all_products_single_class_when_one_item(self):
        items = classify([{"product_id": "P1", "product_name": "X", "total_revenue": 100}])
        summaries = {s.abc_class: s for s in summarize(items)}
        assert summaries["A"].product_count == 1
        assert summaries["B"].product_count == 0
        assert summaries["C"].product_count == 0

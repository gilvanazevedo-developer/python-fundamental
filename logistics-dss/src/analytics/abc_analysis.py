"""
ABC Classification Engine
Pareto-based product classification by cumulative revenue contribution.

Class definitions:
    A — top 70 % of cumulative revenue  (high-value, ~20 % of SKUs)
    B — 70–90 % of cumulative revenue   (medium-value, ~30 % of SKUs)
    C — 90–100 % of cumulative revenue  (low-value, ~50 % of SKUs)
"""

from dataclasses import dataclass
from typing import List

# Default thresholds (configurable per call)
DEFAULT_A_THRESHOLD = 0.70
DEFAULT_B_THRESHOLD = 0.90


@dataclass
class ABCItem:
    """A single product with its ABC classification data."""
    product_id: str
    product_name: str
    category: str
    total_revenue: float
    total_quantity: int
    revenue_pct: float       # This product's share of total revenue (%)
    cumulative_pct: float    # Running cumulative share up to this product (%)
    abc_class: str           # "A", "B", or "C"


@dataclass
class ABCSummary:
    """Aggregated metrics for one ABC class."""
    abc_class: str
    product_count: int
    total_revenue: float
    revenue_pct: float   # % of total revenue held by this class
    product_pct: float   # % of total products in this class


def classify(
    products: List[dict],
    a_threshold: float = DEFAULT_A_THRESHOLD,
    b_threshold: float = DEFAULT_B_THRESHOLD,
) -> List[ABCItem]:
    """
    Classify products into A / B / C based on cumulative revenue contribution.

    Args:
        products:    List of dicts. Required keys:
                       product_id    (str)
                       product_name  (str)
                       total_revenue (float)
                     Optional keys:
                       category      (str)
                       total_quantity (int)
        a_threshold: Cumulative revenue cutoff for class A (default 0.70).
        b_threshold: Cumulative revenue cutoff for class A+B (default 0.90).

    Returns:
        List of ABCItem sorted by revenue descending, with abc_class assigned.
        Products with zero revenue are excluded.
    """
    if not products:
        return []

    # Exclude zero-revenue products; sort highest revenue first
    eligible = [p for p in products if p.get("total_revenue", 0) > 0]
    if not eligible:
        return []

    eligible.sort(key=lambda p: p["total_revenue"], reverse=True)

    grand_total = sum(p["total_revenue"] for p in eligible)

    results: List[ABCItem] = []
    cumulative = 0.0

    for p in eligible:
        share = p["total_revenue"] / grand_total
        cumulative += share

        if cumulative - share < a_threshold:
            # This product's contribution starts before the A threshold
            abc_class = "A"
        elif cumulative - share < b_threshold:
            abc_class = "B"
        else:
            abc_class = "C"

        results.append(ABCItem(
            product_id=p["product_id"],
            product_name=p["product_name"],
            category=p.get("category", ""),
            total_revenue=round(p["total_revenue"], 2),
            total_quantity=int(p.get("total_quantity", 0)),
            revenue_pct=round(share * 100, 2),
            cumulative_pct=round(cumulative * 100, 2),
            abc_class=abc_class,
        ))

    return results


def summarize(items: List[ABCItem]) -> List[ABCSummary]:
    """
    Build a per-class summary from a classified item list.

    Args:
        items: Output of :func:`classify`.

    Returns:
        List of ABCSummary for classes A, B, C (in that order).
        Classes with no products still appear with zero counts.
    """
    if not items:
        return [
            ABCSummary(abc_class=cls, product_count=0,
                       total_revenue=0.0, revenue_pct=0.0, product_pct=0.0)
            for cls in ("A", "B", "C")
        ]

    grand_total = sum(i.total_revenue for i in items)
    total_products = len(items)

    summaries: List[ABCSummary] = []
    for cls in ("A", "B", "C"):
        cls_items = [i for i in items if i.abc_class == cls]
        cls_revenue = sum(i.total_revenue for i in cls_items)
        summaries.append(ABCSummary(
            abc_class=cls,
            product_count=len(cls_items),
            total_revenue=round(cls_revenue, 2),
            revenue_pct=round(cls_revenue / grand_total * 100, 1) if grand_total else 0.0,
            product_pct=round(len(cls_items) / total_products * 100, 1) if total_products else 0.0,
        ))

    return summaries

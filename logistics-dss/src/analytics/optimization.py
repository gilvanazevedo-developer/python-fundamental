"""
Inventory Optimization Engine
Economic Order Quantity (EOQ), safety stock, and reorder point calculations.

All functions are pure (stateless); no database access.

Notation:
    D  — annual demand (units / year)
    S  — ordering cost per order ($ / order)
    H  — holding cost per unit per year ($ / unit / year)
    Q  — order quantity (units)
    Z  — service-level z-score (e.g. 1.65 for 95 %)
    σ  — standard deviation of daily demand (units / day)
    L  — supplier lead time (days)
"""

import math
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    """Full EOQ optimization result for a single product."""

    product_id: str
    product_name: str
    category: str

    # Inputs
    annual_demand: float          # D — units/year
    unit_cost: float              # $/unit
    holding_cost_per_unit: float  # H = unit_cost × carrying_rate  ($/unit/year)
    ordering_cost: float          # S ($/order)
    lead_time_days: int
    service_level_z: float

    # Optimal policy
    eoq: float                    # Q* = √(2DS/H)
    safety_stock: float           # SS = Z × σ × √L
    reorder_point: float          # ROP = daily_demand × L + SS
    orders_per_year: float        # D / Q*

    # Cost at EOQ
    eoq_annual_holding: float     # (Q*/2) × H
    eoq_annual_ordering: float    # (D/Q*) × S
    eoq_total_cost: float         # holding + ordering

    # Cost at current policy (current stock used as order-qty proxy)
    current_order_qty: float
    current_annual_holding: float
    current_annual_ordering: float
    current_total_cost: float

    # Savings
    potential_savings: float      # current_total_cost − eoq_total_cost  (≥ 0)
    savings_pct: float            # savings / current_total_cost × 100   (≥ 0)


# ---------------------------------------------------------------------------
# Core formulas
# ---------------------------------------------------------------------------

def eoq(annual_demand: float, ordering_cost: float, holding_cost_per_unit: float) -> float:
    """
    Economic Order Quantity: Q* = √(2 × D × S / H).

    Returns 0.0 if any input is zero or negative.
    """
    if annual_demand <= 0 or ordering_cost <= 0 or holding_cost_per_unit <= 0:
        return 0.0
    return math.sqrt(2 * annual_demand * ordering_cost / holding_cost_per_unit)


def total_inventory_cost(
    annual_demand: float,
    order_qty: float,
    ordering_cost: float,
    holding_cost_per_unit: float,
) -> dict:
    """
    Total annual inventory cost = ordering cost + holding cost.

    Returns a dict with keys:
        annual_holding   — (Q/2) × H
        annual_ordering  — (D/Q) × S
        total            — sum of above

    Returns all zeros if order_qty <= 0.
    """
    if order_qty <= 0 or annual_demand <= 0:
        return {"annual_holding": 0.0, "annual_ordering": 0.0, "total": 0.0}

    holding = (order_qty / 2) * holding_cost_per_unit
    ordering = (annual_demand / order_qty) * ordering_cost
    return {
        "annual_holding": round(holding, 2),
        "annual_ordering": round(ordering, 2),
        "total": round(holding + ordering, 2),
    }


def safety_stock(
    std_dev_daily: float,
    lead_time_days: int,
    service_level_z: float = 1.65,
) -> float:
    """
    Safety stock = Z × σ_daily × √(lead_time_days).

    Clipped at 0. Returns 0 when std_dev or lead_time is 0.
    """
    if std_dev_daily <= 0 or lead_time_days <= 0:
        return 0.0
    return max(0.0, service_level_z * std_dev_daily * math.sqrt(lead_time_days))


def reorder_point(
    daily_demand: float,
    lead_time_days: int,
    safety_stk: float = 0.0,
) -> float:
    """
    Reorder point = daily_demand × lead_time + safety_stock.

    The result is the inventory level at which a new order should be placed
    so that stock does not run out before the order arrives.
    """
    return max(0.0, daily_demand * lead_time_days + safety_stk)


# ---------------------------------------------------------------------------
# High-level optimisation entry point
# ---------------------------------------------------------------------------

def optimize(
    product_id: str,
    product_name: str,
    category: str,
    daily_demand: float,
    std_dev_daily: float,
    unit_cost: float,
    carrying_cost_rate: float,
    ordering_cost: float,
    lead_time_days: int,
    current_stock: float,
    service_level_z: float = 1.65,
) -> Optional["OptimizationResult"]:
    """
    Compute the full EOQ-based optimisation result for one product.

    Returns None if the product has no demand (daily_demand <= 0) or
    no unit cost (unit_cost <= 0), since optimisation is not meaningful.
    """
    if daily_demand <= 0 or unit_cost <= 0:
        return None

    annual_demand = daily_demand * 365
    holding_cost_per_unit = unit_cost * carrying_cost_rate

    # Optimal policy
    q_star = eoq(annual_demand, ordering_cost, holding_cost_per_unit)
    if q_star <= 0:
        return None

    ss = safety_stock(std_dev_daily, lead_time_days, service_level_z)
    rop = reorder_point(daily_demand, lead_time_days, ss)
    orders_yr = annual_demand / q_star

    eoq_costs = total_inventory_cost(annual_demand, q_star, ordering_cost, holding_cost_per_unit)

    # Current policy: use current_stock as a proxy for the current order qty
    # (assumes the company orders up to current_stock whenever it runs out)
    current_qty = max(current_stock, 1.0)
    current_costs = total_inventory_cost(
        annual_demand, current_qty, ordering_cost, holding_cost_per_unit
    )

    savings = max(0.0, current_costs["total"] - eoq_costs["total"])
    savings_pct = (savings / current_costs["total"] * 100) if current_costs["total"] > 0 else 0.0

    return OptimizationResult(
        product_id=product_id,
        product_name=product_name,
        category=category,
        annual_demand=round(annual_demand, 1),
        unit_cost=round(unit_cost, 2),
        holding_cost_per_unit=round(holding_cost_per_unit, 4),
        ordering_cost=round(ordering_cost, 2),
        lead_time_days=lead_time_days,
        service_level_z=service_level_z,
        eoq=round(q_star, 1),
        safety_stock=round(ss, 1),
        reorder_point=round(rop, 1),
        orders_per_year=round(orders_yr, 1),
        eoq_annual_holding=eoq_costs["annual_holding"],
        eoq_annual_ordering=eoq_costs["annual_ordering"],
        eoq_total_cost=eoq_costs["total"],
        current_order_qty=round(current_qty, 1),
        current_annual_holding=current_costs["annual_holding"],
        current_annual_ordering=current_costs["annual_ordering"],
        current_total_cost=current_costs["total"],
        potential_savings=round(savings, 2),
        savings_pct=round(savings_pct, 1),
    )

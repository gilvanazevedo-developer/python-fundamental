"""
Inventory Service
Query and aggregate inventory data for dashboard display.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal

from sqlalchemy import func, case
from sqlalchemy.orm import Session

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import Product, Warehouse, InventoryLevel, SalesRecord
from src.logger import LoggerMixin


class InventoryService(LoggerMixin):
    """Provides inventory query and aggregation methods."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()

    def get_all_products(
        self,
        category: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all products with their total stock levels."""
        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    Product.id,
                    Product.name,
                    Product.category,
                    Product.unit_cost,
                    Product.unit_price,
                    func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_stock"),
                )
                .outerjoin(InventoryLevel, Product.id == InventoryLevel.product_id)
            )

            if category:
                query = query.filter(Product.category == category)
            if warehouse_id:
                query = query.filter(InventoryLevel.warehouse_id == warehouse_id)
            if search:
                pattern = f"%{search}%"
                query = query.filter(
                    (Product.id.ilike(pattern)) | (Product.name.ilike(pattern))
                )

            query = query.group_by(Product.id)
            rows = query.all()

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "unit_cost": float(r.unit_cost) if r.unit_cost else 0.0,
                    "unit_price": float(r.unit_price) if r.unit_price else 0.0,
                    "total_stock": int(r.total_stock),
                    "stock_value": float(r.unit_cost * r.total_stock) if r.unit_cost else 0.0,
                }
                for r in rows
            ]

    def get_stock_by_product(self, product_id: str) -> List[Dict[str, Any]]:
        """Get stock levels across all warehouses for a product."""
        with self.db_manager.get_session() as session:
            rows = (
                session.query(
                    InventoryLevel.warehouse_id,
                    Warehouse.name.label("warehouse_name"),
                    InventoryLevel.quantity,
                    InventoryLevel.last_updated,
                )
                .join(Warehouse, InventoryLevel.warehouse_id == Warehouse.id)
                .filter(InventoryLevel.product_id == product_id)
                .all()
            )

            return [
                {
                    "warehouse_id": r.warehouse_id,
                    "warehouse_name": r.warehouse_name,
                    "quantity": int(r.quantity),
                    "last_updated": str(r.last_updated) if r.last_updated else None,
                }
                for r in rows
            ]

    def get_stock_summary(
        self,
        category: Optional[str] = None,
        warehouse_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get aggregated stock summary."""
        with self.db_manager.get_session() as session:
            # Total distinct products
            prod_query = session.query(func.count(Product.id))
            if category:
                prod_query = prod_query.filter(Product.category == category)
            total_products = prod_query.scalar() or 0

            # Stock aggregates
            stock_query = session.query(
                func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_units"),
                func.coalesce(
                    func.sum(InventoryLevel.quantity * Product.unit_cost), 0
                ).label("total_value"),
                func.coalesce(
                    func.sum(InventoryLevel.quantity * Product.unit_price), 0
                ).label("total_retail_value"),
            ).join(Product, InventoryLevel.product_id == Product.id)

            if category:
                stock_query = stock_query.filter(Product.category == category)
            if warehouse_id:
                stock_query = stock_query.filter(InventoryLevel.warehouse_id == warehouse_id)

            result = stock_query.one()

            # Products with zero stock
            zero_subquery = (
                session.query(InventoryLevel.product_id)
                .group_by(InventoryLevel.product_id)
                .having(func.sum(InventoryLevel.quantity) > 0)
                .subquery()
            )
            products_with_stock = session.query(
                func.count(zero_subquery.c.product_id)
            ).scalar() or 0
            stockout_count = max(total_products - products_with_stock, 0)

            return {
                "total_products": total_products,
                "total_units": int(result.total_units),
                "total_value": float(result.total_value),
                "total_retail_value": float(result.total_retail_value),
                "stockout_count": stockout_count,
                "products_with_stock": products_with_stock,
            }

    def get_stock_by_category(
        self, warehouse_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get stock aggregated by product category."""
        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    Product.category,
                    func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_units"),
                    func.coalesce(
                        func.sum(InventoryLevel.quantity * Product.unit_cost), 0
                    ).label("total_value"),
                )
                .join(InventoryLevel, Product.id == InventoryLevel.product_id)
                .group_by(Product.category)
            )

            if warehouse_id:
                query = query.filter(InventoryLevel.warehouse_id == warehouse_id)

            rows = query.order_by(func.sum(InventoryLevel.quantity * Product.unit_cost).desc()).all()

            return [
                {
                    "category": r.category,
                    "total_units": int(r.total_units),
                    "total_value": float(r.total_value),
                }
                for r in rows
            ]

    def get_low_stock_items(
        self,
        threshold: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get products with stock at or below a threshold."""
        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    Product.id,
                    Product.name,
                    Product.category,
                    func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_stock"),
                )
                .outerjoin(InventoryLevel, Product.id == InventoryLevel.product_id)
                .group_by(Product.id)
                .having(func.coalesce(func.sum(InventoryLevel.quantity), 0) <= threshold)
            )

            if category:
                query = query.filter(Product.category == category)

            rows = query.order_by(func.coalesce(func.sum(InventoryLevel.quantity), 0).asc()).all()

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "total_stock": int(r.total_stock),
                    "status": "OUT OF STOCK" if r.total_stock == 0 else "LOW STOCK",
                }
                for r in rows
            ]

    def get_categories(self) -> List[str]:
        """Get distinct product categories."""
        with self.db_manager.get_session() as session:
            rows = (
                session.query(Product.category)
                .distinct()
                .order_by(Product.category)
                .all()
            )
            return [r.category for r in rows]

    def get_warehouses(self) -> List[Dict[str, Any]]:
        """Get all warehouses."""
        with self.db_manager.get_session() as session:
            rows = session.query(Warehouse).order_by(Warehouse.name).all()
            return [
                {"id": w.id, "name": w.name, "location": w.location, "capacity": w.capacity}
                for w in rows
            ]

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """Search products by name or ID."""
        return self.get_all_products(search=query)

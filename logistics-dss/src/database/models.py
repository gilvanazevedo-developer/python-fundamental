"""
SQLAlchemy ORM Models for Logistics DSS
Defines the database schema for inventory management.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Date, Text, Boolean,
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Product(Base):
    """Product/SKU master data."""
    __tablename__ = "products"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    inventory_levels = relationship("InventoryLevel", back_populates="product")
    sales_records = relationship("SalesRecord", back_populates="product")

    # Constraints
    __table_args__ = (
        CheckConstraint("unit_cost >= 0", name="check_unit_cost_positive"),
        CheckConstraint("unit_price >= 0", name="check_unit_price_positive"),
    )

    def __repr__(self):
        return f"<Product(id='{self.id}', name='{self.name}')>"


class Warehouse(Base):
    """Warehouse/Location master data."""
    __tablename__ = "warehouses"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    location = Column(String(300), nullable=False)
    capacity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    inventory_levels = relationship("InventoryLevel", back_populates="warehouse")
    sales_records = relationship("SalesRecord", back_populates="warehouse")

    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_capacity_positive"),
    )

    def __repr__(self):
        return f"<Warehouse(id='{self.id}', name='{self.name}')>"


class Supplier(Base):
    """Supplier master data."""
    __tablename__ = "suppliers"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    lead_time_days = Column(Integer, nullable=False)
    min_order_qty = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("lead_time_days >= 0", name="check_lead_time_positive"),
        CheckConstraint("min_order_qty > 0", name="check_min_order_positive"),
    )

    def __repr__(self):
        return f"<Supplier(id='{self.id}', name='{self.name}')>"


class InventoryLevel(Base):
    """Current inventory levels by product and warehouse."""
    __tablename__ = "inventory_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(String(50), ForeignKey("warehouses.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    product = relationship("Product", back_populates="inventory_levels")
    warehouse = relationship("Warehouse", back_populates="inventory_levels")

    __table_args__ = (
        Index("idx_inventory_product_warehouse", "product_id", "warehouse_id", unique=True),
        CheckConstraint("quantity >= 0", name="check_quantity_non_negative"),
    )

    def __repr__(self):
        return f"<InventoryLevel(product='{self.product_id}', warehouse='{self.warehouse_id}', qty={self.quantity})>"


class SalesRecord(Base):
    """Historical sales data."""
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(String(50), ForeignKey("warehouses.id"), nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    revenue = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    product = relationship("Product", back_populates="sales_records")
    warehouse = relationship("Warehouse", back_populates="sales_records")

    __table_args__ = (
        Index("idx_sales_date_product", "date", "product_id"),
        Index("idx_sales_date_warehouse", "date", "warehouse_id"),
        CheckConstraint("quantity_sold >= 0", name="check_qty_sold_positive"),
        CheckConstraint("revenue >= 0", name="check_revenue_positive"),
    )

    def __repr__(self):
        return f"<SalesRecord(date='{self.date}', product='{self.product_id}', qty={self.quantity_sold})>"


class ImportLog(Base):
    """Track data imports for auditing."""
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)  # products, inventory, etc.
    records_total = Column(Integer, nullable=False)
    records_imported = Column(Integer, nullable=False)
    records_failed = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # success, partial, failed
    error_details = Column(Text, nullable=True)
    imported_at = Column(DateTime, default=func.now())
    imported_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<ImportLog(file='{self.filename}', status='{self.status}')>"


# ---------------------------------------------------------------------------
# Phase 8 Models
# ---------------------------------------------------------------------------

class User(Base):
    """Authenticated user with role-based access control."""
    __tablename__ = "user"

    id              = Column(Integer,     primary_key=True, autoincrement=True)
    username        = Column(String(64),  nullable=False, unique=True)
    display_name    = Column(String(128), nullable=True)
    hashed_password = Column(String(256), nullable=False)
    role            = Column(String(16),  nullable=False)   # ADMIN | BUYER | VIEWER
    active          = Column(Boolean,     nullable=False, default=True)
    failed_attempts = Column(Integer,     nullable=False, default=0)
    last_login_at   = Column(DateTime,    nullable=True)
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime,    nullable=False, default=datetime.utcnow,
                                          onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_active_role", "active", "role"),
        Index("idx_user_failed_attempts", "failed_attempts"),
    )

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


class ReportSchedule(Base):
    """Scheduled report configuration persisted in the database."""
    __tablename__ = "report_schedule"

    id              = Column(Integer,     primary_key=True, autoincrement=True)
    report_type     = Column(String(32),  nullable=False)   # INVENTORY | FORECAST | POLICY | EXECUTIVE
    export_format   = Column(String(8),   nullable=False)   # PDF | EXCEL
    cron_expression = Column(String(64),  nullable=False)   # standard 5-field cron
    output_dir      = Column(String(512), nullable=False)
    active          = Column(Boolean,     nullable=False, default=True)
    last_run_at     = Column(DateTime,    nullable=True)
    last_run_status = Column(String(16),  nullable=True)    # SUCCESS | FAILURE | None
    created_by      = Column(String(128), nullable=False)
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime,    nullable=False, default=datetime.utcnow,
                                          onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_schedule_active_type", "active", "report_type"),
        Index("idx_schedule_last_run", "last_run_at"),
    )

    def __repr__(self):
        return f"<ReportSchedule(type='{self.report_type}', cron='{self.cron_expression}')>"


class AuditEvent(Base):
    """Immutable audit trail for all system state-changing operations."""
    __tablename__ = "audit_event"

    id          = Column(Integer,     primary_key=True, autoincrement=True)
    event_type  = Column(String(32),  nullable=False)   # LOGIN | LOGOUT | OPTIMIZATION_RUN | etc.
    actor       = Column(String(128), nullable=False)   # authenticated username
    entity_type = Column(String(32),  nullable=True)    # "OptimizationRun" | "ReportSchedule" | None
    entity_id   = Column(Integer,     nullable=True)    # PK of affected row; NULL for session events
    detail      = Column(Text,        nullable=True)    # JSON-serialised supplementary context
    occurred_at = Column(DateTime,    nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_type_time",   "event_type", "occurred_at"),
        Index("idx_audit_actor_time",  "actor",      "occurred_at"),
        Index("idx_audit_entity",      "entity_type", "entity_id"),
        Index("idx_audit_occurred_at", "occurred_at"),
    )

    def __repr__(self):
        return f"<AuditEvent(type='{self.event_type}', actor='{self.actor}')>"

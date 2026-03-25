"""
Financial models for the grave care service.
Handles pricing, commissions, and revenue tracking.
Uses Decimal for precise money calculations.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text,
    Numeric, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models import Base


# -----------------------------------------------------------------------------
# Service Catalog (with base pricing)
# -----------------------------------------------------------------------------


class ServiceCatalog(Base):
    """Service definitions with base prices."""

    __tablename__ = "service_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pricing_rules: Mapped[list["ServicePricingRule"]] = relationship(
        "ServicePricingRule", back_populates="service", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_service_catalog_active', 'is_active'),
    )


# -----------------------------------------------------------------------------
# Cemetery with Price Multiplier
# -----------------------------------------------------------------------------


class CemeteryPricing(Base):
    """Cemetery locations with price multipliers."""

    __tablename__ = "cemetery_pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    district: Mapped[str | None] = mapped_column(String(200), nullable=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    price_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pricing_rules: Mapped[list["ServicePricingRule"]] = relationship(
        "ServicePricingRule", back_populates="cemetery", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_cemetery_pricing_active', 'is_active'),
        Index('idx_cemetery_pricing_district', 'district'),
        CheckConstraint('price_multiplier > 0', name='check_positive_multiplier'),
    )


# -----------------------------------------------------------------------------
# Service Pricing Rules (per service + cemetery combination)
# -----------------------------------------------------------------------------


class ServicePricingRule(Base):
    """Custom pricing rules per service and/or cemetery."""

    __tablename__ = "service_pricing_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("service_catalog.id", ondelete="CASCADE"), nullable=False
    )
    cemetery_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cemetery_pricing.id", ondelete="CASCADE"), nullable=True
    )

    # Custom price (if null, use base_price * multiplier)
    custom_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Commission percentages (must sum to 100 or less)
    platform_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("30.00")
    )
    worker_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("70.00")
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    service: Mapped["ServiceCatalog"] = relationship("ServiceCatalog", back_populates="pricing_rules")
    cemetery: Mapped["CemeteryPricing | None"] = relationship("CemeteryPricing", back_populates="pricing_rules")

    __table_args__ = (
        Index('idx_pricing_rule_service', 'service_id'),
        Index('idx_pricing_rule_cemetery', 'cemetery_id'),
        Index('idx_pricing_rule_service_cemetery', 'service_id', 'cemetery_id'),
        CheckConstraint('platform_percent >= 0 AND platform_percent <= 100', name='check_platform_percent'),
        CheckConstraint('worker_percent >= 0 AND worker_percent <= 100', name='check_worker_percent'),
    )


# -----------------------------------------------------------------------------
# Order Financial Record
# -----------------------------------------------------------------------------


ORDER_FIN_STATUS_PENDING = "pending"
ORDER_FIN_STATUS_PAID = "paid"
ORDER_FIN_STATUS_COMPLETED = "completed"
ORDER_FIN_STATUS_RETURNED = "returned"
ORDER_FIN_STATUS_CANCELED = "canceled"


class OrderFinancial(Base):
    """Financial record for each order with earnings breakdown."""

    __tablename__ = "order_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to main order (nullable for standalone tracking)
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)

    # User info
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Service & Location
    service_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("service_catalog.id", ondelete="SET NULL"), nullable=True
    )
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)  # Snapshot
    cemetery_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cemetery_pricing.id", ondelete="SET NULL"), nullable=True
    )
    cemetery_name: Mapped[str] = mapped_column(String(300), nullable=False, default="—")  # Snapshot

    # Worker info
    worker_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    worker_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    worker_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Pricing snapshot (at time of order)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    price_multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("1.00"))
    final_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Commission snapshot
    platform_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("30.00"))
    worker_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("70.00"))

    # Calculated earnings (stored permanently)
    platform_earning: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    worker_earning: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ORDER_FIN_STATUS_PENDING)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    service: Mapped["ServiceCatalog | None"] = relationship("ServiceCatalog")
    cemetery: Mapped["CemeteryPricing | None"] = relationship("CemeteryPricing")

    __table_args__ = (
        Index('idx_order_fin_order_id', 'order_id'),
        Index('idx_order_fin_status', 'status'),
        Index('idx_order_fin_worker', 'worker_telegram_id'),
        Index('idx_order_fin_service', 'service_id'),
        Index('idx_order_fin_cemetery', 'cemetery_id'),
        Index('idx_order_fin_created', 'created_at'),
        Index('idx_order_fin_completed', 'completed_at'),
    )


# -----------------------------------------------------------------------------
# Worker Earnings Summary (cached aggregation)
# -----------------------------------------------------------------------------


class WorkerEarnings(Base):
    """Cached worker earnings summary for fast lookups."""

    __tablename__ = "worker_earnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    worker_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    worker_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Totals
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    returned_orders: Mapped[int] = mapped_column(Integer, default=0)
    canceled_orders: Mapped[int] = mapped_column(Integer, default=0)

    # Earnings
    total_earned: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    pending_earnings: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    # Timestamps
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_worker_earnings_telegram', 'worker_telegram_id'),
    )


# -----------------------------------------------------------------------------
# Platform Revenue Summary (daily aggregation)
# -----------------------------------------------------------------------------


class DailyRevenue(Base):
    """Daily revenue aggregation for fast reporting."""

    __tablename__ = "daily_revenue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime, unique=True, nullable=False)

    # Order counts
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    returned_orders: Mapped[int] = mapped_column(Integer, default=0)
    canceled_orders: Mapped[int] = mapped_column(Integer, default=0)

    # Revenue
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    platform_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    worker_payouts: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_daily_revenue_date', 'date'),
    )

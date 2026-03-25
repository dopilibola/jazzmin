"""
Order Analytics Database Models.
Separate module for tracking orders, worker performance, and financial analytics.
Independent from the main analytics system.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, Numeric
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models import Base


# =============================================================================
# Order Analytics - Orders Table
# =============================================================================

class AnalyticsOrder(Base):
    """
    Complete order tracking for analytics.
    Stores full order details for reporting.
    """
    __tablename__ = "order_analytics_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Original order reference
    original_order_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)

    # Customer info
    customer_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Location info
    region_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    district_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cemetery_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cemetery_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Deceased info
    deceased_full_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, index=True)
    birth_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    death_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Financial
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    # Order items summary (JSON string)
    items_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), default='new', nullable=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    posted_to_group_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Time to accept (in seconds)
    time_to_accept_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    acceptance: Mapped[Optional["OrderAcceptance"]] = relationship(
        "OrderAcceptance", back_populates="order", uselist=False
    )
    media: Mapped[list["OrderMedia"]] = relationship(
        "OrderMedia", back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_order_analytics_created', 'created_at'),
        Index('ix_order_analytics_cemetery_date', 'cemetery_id', 'created_at'),
        Index('ix_order_analytics_status_date', 'status', 'created_at'),
    )


# =============================================================================
# Order Acceptance Tracking
# =============================================================================

class OrderAcceptance(Base):
    """
    Tracks when and who accepted each order.
    One-to-one relationship with AnalyticsOrder.
    """
    __tablename__ = "order_analytics_acceptances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Order reference
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("order_analytics_orders.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # Worker info
    worker_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    worker_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    worker_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Timestamps
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    photos_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Performance metrics
    time_to_accept_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_to_complete_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Feedback
    customer_feedback: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'good' or 'bad'

    # Relationship
    order: Mapped["AnalyticsOrder"] = relationship("AnalyticsOrder", back_populates="acceptance")

    __table_args__ = (
        Index('ix_acceptance_worker_date', 'worker_telegram_id', 'accepted_at'),
    )


# =============================================================================
# Worker Statistics (Aggregated)
# =============================================================================

class WorkerStats(Base):
    """
    Aggregated worker performance statistics.
    Updated periodically for fast dashboard queries.
    """
    __tablename__ = "order_analytics_workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Worker info
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Order counts
    total_orders_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_orders_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_orders_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Financial
    total_earnings: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)

    # Performance metrics
    avg_accept_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_complete_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fastest_accept_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Feedback stats
    positive_feedback_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_feedback_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Activity tracking
    first_order_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_order_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Last update
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# =============================================================================
# Order Media (Images)
# =============================================================================

class OrderMedia(Base):
    """
    Stores order-related media (images).
    Includes payment receipts and completion photos.
    """
    __tablename__ = "order_analytics_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Order reference
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("order_analytics_orders.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Media info
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'receipt', 'completion_photo_1', 'completion_photo_2'
    file_id: Mapped[str] = mapped_column(String(500), nullable=False)  # Telegram file_id
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Local path if saved

    # Metadata
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    order: Mapped["AnalyticsOrder"] = relationship("AnalyticsOrder", back_populates="media")


# =============================================================================
# Daily Revenue Summary (Aggregated)
# =============================================================================

class DailyRevenue(Base):
    """
    Daily aggregated revenue statistics.
    One row per day for fast financial reporting.
    """
    __tablename__ = "order_analytics_daily_revenue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Date
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, unique=True, index=True)

    # Order counts
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Revenue
    total_revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)

    # Performance
    avg_accept_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Worker stats
    active_workers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Last update
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

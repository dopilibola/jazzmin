"""
Analytics database models for comprehensive bot tracking.
Tracks users, events, sessions, and button clicks.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models import Base


# =============================================================================
# Analytics Event Model
# =============================================================================

class AnalyticsEvent(Base):
    """
    Tracks all user actions in the bot.
    Every button click, command, state transition is logged here.
    """
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User info
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Event info
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Types: 'command', 'button_click', 'callback', 'message', 'state_enter', 'state_exit'

    event_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    # Examples: '/start', 'btn_services', 'grave:region:1', 'RegistrationState.full_name'

    event_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    # Categories: 'registration', 'grave', 'services', 'flowers', 'payment', 'profile', 'support'

    # Additional data
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for extra data

    # Session tracking
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("analytics_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Time spent on previous action

    # Indexes for fast queries
    __table_args__ = (
        Index('ix_analytics_events_user_time', 'telegram_id', 'timestamp'),
        Index('ix_analytics_events_type_time', 'event_type', 'timestamp'),
        Index('ix_analytics_events_category_time', 'event_category', 'timestamp'),
    )


# =============================================================================
# User Session Model
# =============================================================================

class UserSession(Base):
    """
    Tracks user sessions (from bot entry to exit/inactivity).
    A session starts when user sends first message and ends after 30 min inactivity.
    """
    __tablename__ = "analytics_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User info
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Session timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Session stats
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Entry/exit points
    entry_point: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # First action
    exit_point: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)   # Last action

    # Relationships
    events: Mapped[list["AnalyticsEvent"]] = relationship(
        "AnalyticsEvent", backref="session", lazy="dynamic"
    )

    __table_args__ = (
        Index('ix_sessions_user_active', 'telegram_id', 'is_active'),
        Index('ix_sessions_started', 'started_at'),
    )


# =============================================================================
# Button Statistics Model (Aggregated)
# =============================================================================

class ButtonStats(Base):
    """
    Aggregated button click statistics.
    Updated periodically for fast dashboard queries.
    """
    __tablename__ = "analytics_button_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    button_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    button_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Counts
    total_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    avg_time_spent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Average seconds

    # Last update
    last_clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# =============================================================================
# Daily Statistics Model (Aggregated)
# =============================================================================

class DailyStats(Base):
    """
    Daily aggregated statistics for fast dashboard loading.
    One row per day.
    """
    __tablename__ = "analytics_daily_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, unique=True, index=True)

    # User metrics
    total_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # DAU
    returning_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Event metrics
    total_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Time metrics
    avg_session_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_time_spent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Conversion metrics
    registrations_started: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registrations_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_started: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payments_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# =============================================================================
# User Activity Summary (for retention tracking)
# =============================================================================

class UserActivity(Base):
    """
    Per-user activity summary for retention and engagement tracking.
    """
    __tablename__ = "analytics_user_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Activity dates
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Counts
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_time_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Days active
    days_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Engagement score (calculated)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_ordered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

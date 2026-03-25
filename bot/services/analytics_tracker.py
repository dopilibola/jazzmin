"""
Analytics Tracking Service.
Core service for tracking all bot events, sessions, and user activity.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict

from sqlalchemy import select, func, update, and_, or_, distinct, String
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db import async_session_factory
from bot.database.analytics_models import (
    AnalyticsEvent,
    UserSession,
    ButtonStats,
    DailyStats,
    UserActivity,
)

logger = logging.getLogger(__name__)

# Session timeout (30 minutes of inactivity)
SESSION_TIMEOUT_MINUTES = 30

# Event categories mapping
EVENT_CATEGORIES = {
    # Registration
    '/start': 'registration',
    'lang:': 'registration',
    'registration': 'registration',

    # Grave
    'grave:': 'grave',
    'GraveState': 'grave',

    # Services
    'svc:': 'services',
    'btn_services': 'services',

    # Flowers
    'fl:': 'flowers',
    'btn_flowers': 'flowers',

    # Payment
    'pay:': 'payment',
    'PaymentState': 'payment',
    'checkout': 'payment',

    # Profile
    'profile': 'profile',
    'btn_profile': 'profile',

    # Support
    'support': 'support',
    'btn_support': 'support',

    # About
    'about': 'about',
    'btn_about': 'about',
}


def get_event_category(event_name: str) -> Optional[str]:
    """Determine category from event name."""
    event_lower = event_name.lower()
    for prefix, category in EVENT_CATEGORIES.items():
        if prefix.lower() in event_lower:
            return category
    return 'other'


class AnalyticsTracker:
    """
    Main analytics tracking service.
    Handles event logging, session management, and metrics calculation.
    """

    # In-memory cache for active sessions
    _active_sessions: dict[int, int] = {}  # telegram_id -> session_id
    _last_event_time: dict[int, datetime] = {}  # telegram_id -> last event time
    _last_event_name: dict[int, str] = {}  # telegram_id -> last event name

    @classmethod
    async def track_event(
        cls,
        telegram_id: int,
        event_type: str,
        event_name: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Track a single event.

        Args:
            telegram_id: User's Telegram ID
            event_type: Type of event (command, button_click, callback, message, state_enter, state_exit)
            event_name: Name of the event (e.g., '/start', 'btn_services', 'grave:region:1')
            username: User's Telegram username
            first_name: User's first name
            metadata: Additional event data
        """
        try:
            async with async_session_factory() as session:
                # Get or create session
                session_id = await cls._get_or_create_session(
                    session, telegram_id, username, first_name, event_name
                )

                # Calculate duration from last event
                duration = None
                if telegram_id in cls._last_event_time:
                    delta = datetime.utcnow() - cls._last_event_time[telegram_id]
                    duration = delta.total_seconds()
                    # Cap at session timeout to avoid unrealistic values
                    if duration > SESSION_TIMEOUT_MINUTES * 60:
                        duration = None

                # Create event
                event = AnalyticsEvent(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    event_type=event_type,
                    event_name=event_name,
                    event_category=get_event_category(event_name),
                    extra_data=json.dumps(metadata) if metadata else None,
                    session_id=session_id,
                    timestamp=datetime.utcnow(),
                    duration_seconds=duration,
                )
                session.add(event)

                # Update session event count
                await session.execute(
                    update(UserSession)
                    .where(UserSession.id == session_id)
                    .values(
                        event_count=UserSession.event_count + 1,
                        last_activity_at=datetime.utcnow(),
                        exit_point=event_name,
                    )
                )

                # Update user activity
                await cls._update_user_activity(
                    session, telegram_id, username, first_name, duration
                )

                await session.commit()

                # Update cache
                cls._last_event_time[telegram_id] = datetime.utcnow()
                cls._last_event_name[telegram_id] = event_name

                logger.debug(f"Event tracked: {event_type}:{event_name} for user {telegram_id}")

        except Exception as e:
            logger.error(f"Failed to track event: {e}")

    @classmethod
    async def _get_or_create_session(
        cls,
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        entry_point: str,
    ) -> int:
        """Get existing active session or create new one."""
        # Check cache first
        if telegram_id in cls._active_sessions:
            # Check if session is still valid (not timed out)
            if telegram_id in cls._last_event_time:
                delta = datetime.utcnow() - cls._last_event_time[telegram_id]
                if delta.total_seconds() < SESSION_TIMEOUT_MINUTES * 60:
                    return cls._active_sessions[telegram_id]

            # Session timed out, close it
            await cls._close_session(session, cls._active_sessions[telegram_id])
            del cls._active_sessions[telegram_id]

        # Check database for active session
        result = await session.execute(
            select(UserSession)
            .where(
                UserSession.telegram_id == telegram_id,
                UserSession.is_active == True,
                UserSession.last_activity_at > datetime.utcnow() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            )
            .order_by(UserSession.started_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            cls._active_sessions[telegram_id] = existing.id
            return existing.id

        # Create new session
        new_session = UserSession(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
            entry_point=entry_point,
            is_active=True,
        )
        session.add(new_session)
        await session.flush()

        cls._active_sessions[telegram_id] = new_session.id
        return new_session.id

    @classmethod
    async def _close_session(cls, session: AsyncSession, session_id: int) -> None:
        """Close a session and calculate duration."""
        result = await session.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        user_session = result.scalar_one_or_none()

        if user_session and user_session.is_active:
            duration = (user_session.last_activity_at - user_session.started_at).total_seconds()
            await session.execute(
                update(UserSession)
                .where(UserSession.id == session_id)
                .values(
                    is_active=False,
                    ended_at=user_session.last_activity_at,
                    duration_seconds=duration,
                )
            )

    @classmethod
    async def _update_user_activity(
        cls,
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        duration: Optional[float],
    ) -> None:
        """Update user activity record."""
        result = await session.execute(
            select(UserActivity).where(UserActivity.telegram_id == telegram_id)
        )
        activity = result.scalar_one_or_none()

        if activity:
            activity.last_seen_at = datetime.utcnow()
            activity.total_events += 1
            if duration:
                activity.total_time_spent += duration
            if username:
                activity.username = username
            if first_name:
                activity.first_name = first_name
        else:
            activity = UserActivity(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(),
                total_events=1,
                total_time_spent=duration or 0,
            )
            session.add(activity)

    @classmethod
    async def close_inactive_sessions(cls) -> int:
        """Close all sessions that have been inactive for too long."""
        cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        closed = 0

        async with async_session_factory() as session:
            result = await session.execute(
                select(UserSession)
                .where(
                    UserSession.is_active == True,
                    UserSession.last_activity_at < cutoff
                )
            )
            sessions_to_close = result.scalars().all()

            for user_session in sessions_to_close:
                duration = (user_session.last_activity_at - user_session.started_at).total_seconds()
                user_session.is_active = False
                user_session.ended_at = user_session.last_activity_at
                user_session.duration_seconds = duration
                closed += 1

                # Remove from cache
                if user_session.telegram_id in cls._active_sessions:
                    del cls._active_sessions[user_session.telegram_id]

            await session.commit()

        return closed


# =============================================================================
# Analytics Query Functions
# =============================================================================

async def get_total_users() -> int:
    """Get total number of unique users."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.count(distinct(AnalyticsEvent.telegram_id)))
        )
        return result.scalar() or 0


async def get_new_users_today() -> int:
    """Get number of new users today."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.count(distinct(UserActivity.telegram_id)))
            .where(UserActivity.first_seen_at >= today)
        )
        return result.scalar() or 0


async def get_active_users(hours: int = 24) -> int:
    """Get number of active users in last N hours (DAU/WAU)."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.count(distinct(AnalyticsEvent.telegram_id)))
            .where(AnalyticsEvent.timestamp >= cutoff)
        )
        return result.scalar() or 0


async def get_button_stats(limit: int = 20) -> list[dict]:
    """Get most clicked buttons."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                AnalyticsEvent.event_name,
                AnalyticsEvent.event_category,
                func.count(AnalyticsEvent.id).label('clicks'),
                func.count(distinct(AnalyticsEvent.telegram_id)).label('unique_users'),
                func.avg(AnalyticsEvent.duration_seconds).label('avg_duration'),
            )
            .where(AnalyticsEvent.event_type.in_(['button_click', 'callback']))
            .group_by(AnalyticsEvent.event_name, AnalyticsEvent.event_category)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .limit(limit)
        )
        return [
            {
                'name': row.event_name,
                'category': row.event_category,
                'clicks': row.clicks,
                'unique_users': row.unique_users,
                'avg_duration': round(row.avg_duration, 2) if row.avg_duration else None,
            }
            for row in result
        ]


async def get_session_stats(hours: int = 24) -> dict:
    """Get session statistics."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.count(UserSession.id).label('total_sessions'),
                func.avg(UserSession.duration_seconds).label('avg_duration'),
                func.sum(UserSession.duration_seconds).label('total_duration'),
                func.avg(UserSession.event_count).label('avg_events'),
            )
            .where(UserSession.started_at >= cutoff)
        )
        row = result.one()
        return {
            'total_sessions': row.total_sessions or 0,
            'avg_duration': round(row.avg_duration or 0, 2),
            'total_duration': round(row.total_duration or 0, 2),
            'avg_events_per_session': round(row.avg_events or 0, 2),
        }


async def get_hourly_activity(hours: int = 24) -> dict[int, int]:
    """Get event count by hour."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        # SQLite compatible hour extraction
        result = await session.execute(
            select(
                func.strftime('%H', AnalyticsEvent.timestamp).label('hour'),
                func.count(AnalyticsEvent.id).label('count'),
            )
            .where(AnalyticsEvent.timestamp >= cutoff)
            .group_by(func.strftime('%H', AnalyticsEvent.timestamp))
        )
        return {int(row.hour): row.count for row in result}


async def get_daily_activity(days: int = 7) -> list[dict]:
    """Get daily user activity."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.date(AnalyticsEvent.timestamp).label('date'),
                func.count(distinct(AnalyticsEvent.telegram_id)).label('users'),
                func.count(AnalyticsEvent.id).label('events'),
            )
            .where(AnalyticsEvent.timestamp >= cutoff)
            .group_by(func.date(AnalyticsEvent.timestamp))
            .order_by(func.date(AnalyticsEvent.timestamp))
        )
        return [
            {
                'date': str(row.date),
                'users': row.users,
                'events': row.events,
            }
            for row in result
        ]


async def get_drop_off_points(hours: int = 24) -> list[dict]:
    """Find where users leave the bot (last action before session end)."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                UserSession.exit_point,
                func.count(UserSession.id).label('count'),
            )
            .where(
                UserSession.started_at >= cutoff,
                UserSession.exit_point.isnot(None),
                UserSession.is_active == False,
            )
            .group_by(UserSession.exit_point)
            .order_by(func.count(UserSession.id).desc())
            .limit(10)
        )
        return [
            {'exit_point': row.exit_point, 'count': row.count}
            for row in result
        ]


async def get_most_active_users(limit: int = 10) -> list[dict]:
    """Get most active users."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserActivity)
            .order_by(UserActivity.total_events.desc())
            .limit(limit)
        )
        return [
            {
                'telegram_id': u.telegram_id,
                'username': u.username,
                'first_name': u.first_name,
                'total_events': u.total_events,
                'total_sessions': u.total_sessions,
                'total_time_spent': round(u.total_time_spent / 60, 2),  # minutes
                'first_seen': u.first_seen_at.isoformat(),
                'last_seen': u.last_seen_at.isoformat(),
            }
            for u in result.scalars()
        ]


async def get_retention_rate(days: int = 7) -> float:
    """Calculate retention rate (returning users / total users)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with async_session_factory() as session:
        # Users who were active in the period
        active_result = await session.execute(
            select(func.count(distinct(UserActivity.telegram_id)))
            .where(UserActivity.last_seen_at >= cutoff)
        )
        active_users = active_result.scalar() or 0

        # Users who were first seen before the period but are still active
        returning_result = await session.execute(
            select(func.count(distinct(UserActivity.telegram_id)))
            .where(
                UserActivity.first_seen_at < cutoff,
                UserActivity.last_seen_at >= cutoff,
            )
        )
        returning_users = returning_result.scalar() or 0

        if active_users == 0:
            return 0.0

        return round((returning_users / active_users) * 100, 2)


async def get_category_stats(hours: int = 24) -> dict[str, int]:
    """Get event counts by category."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                AnalyticsEvent.event_category,
                func.count(AnalyticsEvent.id).label('count'),
            )
            .where(
                AnalyticsEvent.timestamp >= cutoff,
                AnalyticsEvent.event_category.isnot(None),
            )
            .group_by(AnalyticsEvent.event_category)
        )
        return {row.event_category: row.count for row in result}


async def get_funnel_stats(hours: int = 24) -> dict:
    """Get funnel conversion stats."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        # Define funnel stages
        stages = {
            'start': '/start',
            'registration': 'registration_complete',
            'grave_started': 'grave:region',
            'grave_completed': 'grave_complete',
            'service_viewed': 'services_view',
            'order_started': 'service_order',
            'payment_started': 'checkout_start',
            'payment_completed': 'payment_confirmed',
        }

        funnel = {}
        for stage_name, event_pattern in stages.items():
            result = await session.execute(
                select(func.count(distinct(AnalyticsEvent.telegram_id)))
                .where(
                    AnalyticsEvent.timestamp >= cutoff,
                    AnalyticsEvent.event_name.contains(event_pattern),
                )
            )
            funnel[stage_name] = result.scalar() or 0

        return funnel


async def get_time_spent_by_step(hours: int = 24) -> list[dict]:
    """Get average time spent on each step/state."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                AnalyticsEvent.event_name,
                AnalyticsEvent.event_category,
                func.avg(AnalyticsEvent.duration_seconds).label('avg_time'),
                func.count(AnalyticsEvent.id).label('occurrences'),
            )
            .where(
                AnalyticsEvent.timestamp >= cutoff,
                AnalyticsEvent.duration_seconds.isnot(None),
                AnalyticsEvent.duration_seconds > 0,
                AnalyticsEvent.duration_seconds < 3600,  # Less than 1 hour
            )
            .group_by(AnalyticsEvent.event_name, AnalyticsEvent.event_category)
            .having(func.count(AnalyticsEvent.id) >= 3)  # At least 3 occurrences
            .order_by(func.avg(AnalyticsEvent.duration_seconds).desc())
            .limit(20)
        )
        return [
            {
                'step': row.event_name,
                'category': row.event_category,
                'avg_time_seconds': round(row.avg_time, 2),
                'occurrences': row.occurrences,
            }
            for row in result
        ]


# =============================================================================
# User Tracking & Journey Functions
# =============================================================================

async def get_all_users_with_journey(
    search: str = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    Get all users with their last action and journey info.
    Returns (users_list, total_count)
    """
    async with async_session_factory() as session:
        # Base query for user activity
        query = select(UserActivity).order_by(UserActivity.last_seen_at.desc())
        count_query = select(func.count(UserActivity.id))

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            search_filter = or_(
                UserActivity.telegram_id.cast(String).contains(search),
                UserActivity.username.ilike(search_pattern),
                UserActivity.first_name.ilike(search_pattern),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Get total count
        total_result = await session.execute(count_query)
        total_count = total_result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        users = result.scalars().all()

        # Get last session exit point for each user
        user_data = []
        for u in users:
            # Get last session info
            last_session_result = await session.execute(
                select(UserSession)
                .where(UserSession.telegram_id == u.telegram_id)
                .order_by(UserSession.started_at.desc())
                .limit(1)
            )
            last_session = last_session_result.scalar_one_or_none()

            user_data.append({
                'telegram_id': u.telegram_id,
                'username': u.username,
                'first_name': u.first_name,
                'total_events': u.total_events,
                'total_sessions': u.total_sessions,
                'total_time_spent': round(u.total_time_spent / 60, 1),  # minutes
                'first_seen': u.first_seen_at,
                'last_seen': u.last_seen_at,
                'is_registered': u.is_registered,
                'has_ordered': u.has_ordered,
                'last_action': last_session.exit_point if last_session else None,
                'last_entry': last_session.entry_point if last_session else None,
            })

        return user_data, total_count


async def get_user_journey_details(telegram_id: int) -> dict:
    """Get detailed journey for a specific user."""
    async with async_session_factory() as session:
        # Get user activity
        activity_result = await session.execute(
            select(UserActivity).where(UserActivity.telegram_id == telegram_id)
        )
        activity = activity_result.scalar_one_or_none()

        if not activity:
            return None

        # Get all events for this user (last 100)
        events_result = await session.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.telegram_id == telegram_id)
            .order_by(AnalyticsEvent.timestamp.desc())
            .limit(100)
        )
        events = events_result.scalars().all()

        # Get all sessions for this user
        sessions_result = await session.execute(
            select(UserSession)
            .where(UserSession.telegram_id == telegram_id)
            .order_by(UserSession.started_at.desc())
            .limit(20)
        )
        sessions = sessions_result.scalars().all()

        # Analyze journey stages
        journey_stages = {
            'started': False,
            'registered': False,
            'added_grave': False,
            'viewed_services': False,
            'added_to_cart': False,
            'started_checkout': False,
            'completed_payment': False,
        }

        event_names = [e.event_name for e in events]

        for event_name in event_names:
            event_lower = event_name.lower()
            if '/start' in event_lower:
                journey_stages['started'] = True
            if 'registration' in event_lower or 'phone' in event_lower:
                journey_stages['registered'] = True
            if 'grave' in event_lower and 'complete' in event_lower:
                journey_stages['added_grave'] = True
            if 'service' in event_lower or 'flower' in event_lower:
                journey_stages['viewed_services'] = True
            if 'cart' in event_lower:
                journey_stages['added_to_cart'] = True
            if 'checkout' in event_lower:
                journey_stages['started_checkout'] = True
            if 'payment' in event_lower and 'confirm' in event_lower:
                journey_stages['completed_payment'] = True

        # Determine current stage / drop-off point
        if journey_stages['completed_payment']:
            current_stage = 'To\'lov amalga oshirilgan ✅'
            stage_index = 7
        elif journey_stages['started_checkout']:
            current_stage = 'To\'lov boshlagan (tugallanmagan)'
            stage_index = 6
        elif journey_stages['added_to_cart']:
            current_stage = 'Savatchaga qo\'shgan'
            stage_index = 5
        elif journey_stages['viewed_services']:
            current_stage = 'Xizmatlarni ko\'rgan'
            stage_index = 4
        elif journey_stages['added_grave']:
            current_stage = 'Qabr qo\'shgan'
            stage_index = 3
        elif journey_stages['registered']:
            current_stage = 'Ro\'yxatdan o\'tgan'
            stage_index = 2
        elif journey_stages['started']:
            current_stage = '/start bosgan (ro\'yxatdan o\'tmagan)'
            stage_index = 1
        else:
            current_stage = 'Noma\'lum'
            stage_index = 0

        return {
            'telegram_id': telegram_id,
            'username': activity.username,
            'first_name': activity.first_name,
            'first_seen': activity.first_seen_at,
            'last_seen': activity.last_seen_at,
            'total_events': activity.total_events,
            'total_sessions': activity.total_sessions,
            'total_time_spent': round(activity.total_time_spent / 60, 1),
            'current_stage': current_stage,
            'stage_index': stage_index,
            'journey_stages': journey_stages,
            'recent_events': [
                {
                    'name': e.event_name,
                    'type': e.event_type,
                    'category': e.event_category,
                    'timestamp': e.timestamp,
                    'duration': round(e.duration_seconds, 1) if e.duration_seconds else None,
                }
                for e in events[:30]
            ],
            'sessions': [
                {
                    'id': s.id,
                    'started_at': s.started_at,
                    'ended_at': s.ended_at,
                    'duration': round(s.duration_seconds / 60, 1) if s.duration_seconds else None,
                    'entry_point': s.entry_point,
                    'exit_point': s.exit_point,
                    'event_count': s.event_count,
                    'is_active': s.is_active,
                }
                for s in sessions
            ],
        }


async def get_users_by_stage() -> dict[str, int]:
    """Get count of users at each stage of the funnel."""
    async with async_session_factory() as session:
        # Get all user activities
        result = await session.execute(select(UserActivity))
        users = result.scalars().all()

        stages = {
            'all_users': len(users),
            'registered': 0,
            'added_grave': 0,
            'viewed_services': 0,
            'started_checkout': 0,
            'completed_payment': 0,
        }

        stages['registered'] = sum(1 for u in users if u.is_registered)
        stages['completed_payment'] = sum(1 for u in users if u.has_ordered)

        return stages


async def get_drop_off_users(hours: int = 168, limit: int = 50) -> list[dict]:
    """Get users who dropped off (have sessions that ended without payment)."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with async_session_factory() as session:
        # Get users with closed sessions, ordered by recency
        result = await session.execute(
            select(
                UserSession.telegram_id,
                UserSession.exit_point,
                UserSession.started_at,
                UserSession.ended_at,
                UserSession.duration_seconds,
                UserActivity.username,
                UserActivity.first_name,
                UserActivity.total_events,
            )
            .join(UserActivity, UserSession.telegram_id == UserActivity.telegram_id)
            .where(
                UserSession.started_at >= cutoff,
                UserSession.is_active == False,
                UserSession.exit_point.isnot(None),
            )
            .order_by(UserSession.ended_at.desc())
            .limit(limit)
        )

        return [
            {
                'telegram_id': row.telegram_id,
                'username': row.username,
                'first_name': row.first_name,
                'exit_point': row.exit_point,
                'session_start': row.started_at,
                'session_end': row.ended_at,
                'duration': round(row.duration_seconds / 60, 1) if row.duration_seconds else None,
                'total_events': row.total_events,
            }
            for row in result
        ]

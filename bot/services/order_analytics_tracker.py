"""
Order Analytics Tracking Service.
Tracks orders, worker performance, and financial data.
Independent from the main analytics system.
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import select, func, update, and_, or_, distinct, desc, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db import async_session_factory
from bot.database.order_analytics_models import (
    AnalyticsOrder,
    OrderAcceptance,
    WorkerStats,
    OrderMedia,
    DailyRevenue,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Order Tracking Functions
# =============================================================================

class OrderAnalyticsTracker:
    """
    Main tracker for order analytics.
    Call these methods from order handlers to track events.
    """

    @classmethod
    async def track_order_created(
        cls,
        original_order_id: int,
        customer_telegram_id: int,
        customer_name: str = None,
        customer_phone: str = None,
        region_name: str = None,
        district_name: str = None,
        cemetery_name: str = None,
        cemetery_id: int = None,
        deceased_full_name: str = None,
        birth_year: int = None,
        death_year: int = None,
        total_price: float = 0,
        items_summary: str = None,
    ) -> Optional[int]:
        """Track when a new order is created."""
        try:
            async with async_session_factory() as session:
                # Check if already exists
                existing = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                if existing.scalar_one_or_none():
                    return None

                order = AnalyticsOrder(
                    original_order_id=original_order_id,
                    customer_telegram_id=customer_telegram_id,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    region_name=region_name,
                    district_name=district_name,
                    cemetery_name=cemetery_name,
                    cemetery_id=cemetery_id,
                    deceased_full_name=deceased_full_name,
                    birth_year=birth_year,
                    death_year=death_year,
                    total_price=total_price,
                    items_summary=items_summary,
                    status='new',
                    created_at=datetime.utcnow(),
                )
                session.add(order)
                await session.commit()
                await session.refresh(order)

                logger.info(f"Order analytics: tracked new order #{original_order_id}")
                return order.id

        except Exception as e:
            logger.error(f"Error tracking order creation: {e}")
            return None

    @classmethod
    async def track_order_posted_to_group(cls, original_order_id: int) -> bool:
        """Track when order is posted to Telegram group."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                order = result.scalar_one_or_none()

                if order:
                    order.posted_to_group_at = datetime.utcnow()
                    order.status = 'posted'
                    await session.commit()
                    logger.info(f"Order analytics: order #{original_order_id} posted to group")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error tracking order posted: {e}")
            return False

    @classmethod
    async def track_order_accepted(
        cls,
        original_order_id: int,
        worker_telegram_id: int,
        worker_username: str = None,
        worker_name: str = None,
    ) -> bool:
        """Track when a worker accepts an order."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                order = result.scalar_one_or_none()

                if not order:
                    logger.warning(f"Order #{original_order_id} not found in analytics")
                    return False

                now = datetime.utcnow()

                # Calculate time to accept
                time_to_accept = None
                if order.posted_to_group_at:
                    time_to_accept = (now - order.posted_to_group_at).total_seconds()

                # Update order
                order.accepted_at = now
                order.time_to_accept_seconds = time_to_accept
                order.status = 'in_progress'

                # Create acceptance record
                acceptance = OrderAcceptance(
                    order_id=order.id,
                    worker_telegram_id=worker_telegram_id,
                    worker_username=worker_username,
                    worker_name=worker_name,
                    accepted_at=now,
                    time_to_accept_seconds=time_to_accept,
                )
                session.add(acceptance)

                # Update worker stats
                await cls._update_worker_stats_on_accept(
                    session, worker_telegram_id, worker_username, worker_name,
                    time_to_accept, float(order.total_price)
                )

                await session.commit()
                logger.info(f"Order analytics: order #{original_order_id} accepted by {worker_telegram_id}")
                return True

        except Exception as e:
            logger.error(f"Error tracking order acceptance: {e}")
            return False

    @classmethod
    async def track_order_completed(
        cls,
        original_order_id: int,
        customer_feedback: str = None,
    ) -> bool:
        """Track when an order is completed (photos verified)."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                order = result.scalar_one_or_none()

                if not order:
                    return False

                now = datetime.utcnow()
                order.completed_at = now
                order.status = 'completed'

                # Get acceptance record separately (avoid lazy loading issues)
                acceptance_result = await session.execute(
                    select(OrderAcceptance).where(OrderAcceptance.order_id == order.id)
                )
                acceptance = acceptance_result.scalar_one_or_none()

                if acceptance:
                    acceptance.is_completed = True
                    acceptance.verified_at = now
                    if acceptance.accepted_at:
                        acceptance.time_to_complete_seconds = (
                            now - acceptance.accepted_at
                        ).total_seconds()

                    if customer_feedback:
                        acceptance.customer_feedback = customer_feedback

                    # Update worker stats for completion
                    await cls._update_worker_stats_on_complete(
                        session,
                        acceptance.worker_telegram_id,
                        float(order.total_price),
                        customer_feedback,
                    )

                # Update daily revenue
                await cls._update_daily_revenue(session, float(order.total_price))

                await session.commit()
                logger.info(f"Order analytics: order #{original_order_id} completed")
                return True

        except Exception as e:
            logger.error(f"Error tracking order completion: {e}")
            return False

    @classmethod
    async def track_order_rejected(cls, original_order_id: int) -> bool:
        """Track when an order's photos are rejected."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                order = result.scalar_one_or_none()

                if not order:
                    return False

                # Get acceptance record separately
                acceptance_result = await session.execute(
                    select(OrderAcceptance).where(OrderAcceptance.order_id == order.id)
                )
                acceptance = acceptance_result.scalar_one_or_none()

                if acceptance:
                    acceptance.is_rejected = True

                    # Update worker rejection count
                    await session.execute(
                        update(WorkerStats)
                        .where(WorkerStats.telegram_id == acceptance.worker_telegram_id)
                        .values(total_orders_rejected=WorkerStats.total_orders_rejected + 1)
                    )

                    await session.commit()
                    return True
                return False

        except Exception as e:
            logger.error(f"Error tracking order rejection: {e}")
            return False

    @classmethod
    async def track_photos_submitted(
        cls,
        original_order_id: int,
        photo1_file_id: str = None,
        photo2_file_id: str = None,
    ) -> bool:
        """Track when worker submits completion photos."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                order = result.scalar_one_or_none()

                if not order:
                    return False

                now = datetime.utcnow()

                # Update acceptance record separately
                acceptance_result = await session.execute(
                    select(OrderAcceptance).where(OrderAcceptance.order_id == order.id)
                )
                acceptance = acceptance_result.scalar_one_or_none()
                if acceptance:
                    acceptance.photos_submitted_at = now

                # Add media records
                if photo1_file_id:
                    media1 = OrderMedia(
                        order_id=order.id,
                        media_type='completion_photo_1',
                        file_id=photo1_file_id,
                        uploaded_at=now,
                    )
                    session.add(media1)

                if photo2_file_id:
                    media2 = OrderMedia(
                        order_id=order.id,
                        media_type='completion_photo_2',
                        file_id=photo2_file_id,
                        uploaded_at=now,
                    )
                    session.add(media2)

                await session.commit()
                return True

        except Exception as e:
            logger.error(f"Error tracking photos: {e}")
            return False

    @classmethod
    async def track_customer_feedback(
        cls,
        original_order_id: int,
        feedback: str,  # 'good' or 'bad'
    ) -> bool:
        """Track customer feedback for completed order."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AnalyticsOrder).where(
                        AnalyticsOrder.original_order_id == original_order_id
                    )
                )
                order = result.scalar_one_or_none()

                if not order:
                    return False

                # Get acceptance record separately
                acceptance_result = await session.execute(
                    select(OrderAcceptance).where(OrderAcceptance.order_id == order.id)
                )
                acceptance = acceptance_result.scalar_one_or_none()

                if acceptance:
                    acceptance.customer_feedback = feedback

                    # Update worker feedback stats
                    if feedback == 'good':
                        await session.execute(
                            update(WorkerStats)
                            .where(WorkerStats.telegram_id == acceptance.worker_telegram_id)
                            .values(positive_feedback_count=WorkerStats.positive_feedback_count + 1)
                        )
                    elif feedback == 'bad':
                        await session.execute(
                            update(WorkerStats)
                            .where(WorkerStats.telegram_id == acceptance.worker_telegram_id)
                            .values(negative_feedback_count=WorkerStats.negative_feedback_count + 1)
                        )

                    await session.commit()
                    return True
                return False

        except Exception as e:
            logger.error(f"Error tracking feedback: {e}")
            return False

    # -------------------------------------------------------------------------
    # Helper methods for stats updates
    # -------------------------------------------------------------------------

    @classmethod
    async def _update_worker_stats_on_accept(
        cls,
        session: AsyncSession,
        worker_id: int,
        username: str,
        name: str,
        accept_time: float,
        order_price: float,
    ):
        """Update worker stats when order is accepted."""
        result = await session.execute(
            select(WorkerStats).where(WorkerStats.telegram_id == worker_id)
        )
        stats = result.scalar_one_or_none()

        now = datetime.utcnow()

        if stats:
            stats.total_orders_accepted += 1
            stats.last_order_at = now
            if username:
                stats.username = username
            if name:
                stats.display_name = name

            # Update average accept time
            if accept_time and stats.avg_accept_time_seconds:
                total = stats.avg_accept_time_seconds * (stats.total_orders_accepted - 1)
                stats.avg_accept_time_seconds = (total + accept_time) / stats.total_orders_accepted
            elif accept_time:
                stats.avg_accept_time_seconds = accept_time

            # Update fastest
            if accept_time:
                if not stats.fastest_accept_seconds or accept_time < stats.fastest_accept_seconds:
                    stats.fastest_accept_seconds = accept_time

            stats.updated_at = now
        else:
            stats = WorkerStats(
                telegram_id=worker_id,
                username=username,
                display_name=name,
                total_orders_accepted=1,
                avg_accept_time_seconds=accept_time,
                fastest_accept_seconds=accept_time,
                first_order_at=now,
                last_order_at=now,
                updated_at=now,
            )
            session.add(stats)

    @classmethod
    async def _update_worker_stats_on_complete(
        cls,
        session: AsyncSession,
        worker_id: int,
        order_price: float,
        feedback: str = None,
    ):
        """Update worker stats when order is completed."""
        await session.execute(
            update(WorkerStats)
            .where(WorkerStats.telegram_id == worker_id)
            .values(
                total_orders_completed=WorkerStats.total_orders_completed + 1,
                total_earnings=WorkerStats.total_earnings + Decimal(str(order_price)),
                updated_at=datetime.utcnow(),
            )
        )

    @classmethod
    async def _update_daily_revenue(cls, session: AsyncSession, amount: float):
        """Update daily revenue record."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = await session.execute(
            select(DailyRevenue).where(DailyRevenue.date == today)
        )
        daily = result.scalar_one_or_none()

        if daily:
            daily.completed_orders += 1
            daily.total_revenue = float(daily.total_revenue) + amount
            daily.updated_at = datetime.utcnow()
        else:
            daily = DailyRevenue(
                date=today,
                total_orders=1,
                completed_orders=1,
                total_revenue=amount,
                updated_at=datetime.utcnow(),
            )
            session.add(daily)


# =============================================================================
# Analytics Query Functions
# =============================================================================

async def get_order_analytics_summary(days: int = 30) -> dict:
    """Get overall order analytics summary."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    async with async_session_factory() as session:
        # Total orders
        total_result = await session.execute(
            select(func.count(AnalyticsOrder.id))
            .where(AnalyticsOrder.created_at >= cutoff)
        )
        total_orders = total_result.scalar() or 0

        # Completed orders
        completed_result = await session.execute(
            select(func.count(AnalyticsOrder.id))
            .where(
                AnalyticsOrder.created_at >= cutoff,
                AnalyticsOrder.status == 'completed'
            )
        )
        completed_orders = completed_result.scalar() or 0

        # Total revenue
        revenue_result = await session.execute(
            select(func.sum(AnalyticsOrder.total_price))
            .where(
                AnalyticsOrder.created_at >= cutoff,
                AnalyticsOrder.status == 'completed'
            )
        )
        total_revenue = float(revenue_result.scalar() or 0)

        # Average acceptance time
        avg_time_result = await session.execute(
            select(func.avg(AnalyticsOrder.time_to_accept_seconds))
            .where(
                AnalyticsOrder.created_at >= cutoff,
                AnalyticsOrder.time_to_accept_seconds.isnot(None)
            )
        )
        avg_accept_time = avg_time_result.scalar() or 0

        # Fastest / slowest acceptance
        min_max_result = await session.execute(
            select(
                func.min(AnalyticsOrder.time_to_accept_seconds),
                func.max(AnalyticsOrder.time_to_accept_seconds)
            )
            .where(
                AnalyticsOrder.created_at >= cutoff,
                AnalyticsOrder.time_to_accept_seconds.isnot(None),
                AnalyticsOrder.time_to_accept_seconds > 0
            )
        )
        row = min_max_result.one()
        fastest_accept = row[0] or 0
        slowest_accept = row[1] or 0

        # Active workers count
        workers_result = await session.execute(
            select(func.count(distinct(OrderAcceptance.worker_telegram_id)))
            .where(OrderAcceptance.accepted_at >= cutoff)
        )
        active_workers = workers_result.scalar() or 0

        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'completion_rate': round(completed_orders / total_orders * 100, 1) if total_orders > 0 else 0,
            'total_revenue': total_revenue,
            'avg_accept_time_seconds': round(avg_accept_time, 2) if avg_accept_time else 0,
            'avg_accept_time_formatted': format_duration(avg_accept_time),
            'fastest_accept_seconds': round(fastest_accept, 2),
            'fastest_accept_formatted': format_duration(fastest_accept),
            'slowest_accept_seconds': round(slowest_accept, 2),
            'slowest_accept_formatted': format_duration(slowest_accept),
            'active_workers': active_workers,
        }


async def get_top_workers(limit: int = 10) -> list[dict]:
    """Get top performing workers."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(WorkerStats)
            .order_by(desc(WorkerStats.total_orders_completed))
            .limit(limit)
        )
        workers = result.scalars().all()

        return [
            {
                'telegram_id': w.telegram_id,
                'username': w.username,
                'display_name': w.display_name,
                'total_accepted': w.total_orders_accepted,
                'total_completed': w.total_orders_completed,
                'total_earnings': float(w.total_earnings),
                'avg_accept_time': format_duration(w.avg_accept_time_seconds),
                'avg_accept_seconds': w.avg_accept_time_seconds or 0,
                'fastest_accept': format_duration(w.fastest_accept_seconds),
                'positive_feedback': w.positive_feedback_count,
                'negative_feedback': w.negative_feedback_count,
                'rating': calculate_worker_rating(w),
                'last_order_at': w.last_order_at,
            }
            for w in workers
        ]


async def get_fastest_workers(limit: int = 10) -> list[dict]:
    """Get workers with fastest acceptance times."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(WorkerStats)
            .where(WorkerStats.avg_accept_time_seconds.isnot(None))
            .order_by(WorkerStats.avg_accept_time_seconds)
            .limit(limit)
        )
        workers = result.scalars().all()

        return [
            {
                'telegram_id': w.telegram_id,
                'username': w.username,
                'display_name': w.display_name,
                'avg_accept_time': format_duration(w.avg_accept_time_seconds),
                'avg_accept_seconds': w.avg_accept_time_seconds or 0,
                'fastest_accept': format_duration(w.fastest_accept_seconds),
                'total_completed': w.total_orders_completed,
            }
            for w in workers
        ]


async def get_revenue_stats(days: int = 30) -> dict:
    """Get revenue statistics."""
    async with async_session_factory() as session:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Daily revenue (today)
        daily_result = await session.execute(
            select(func.sum(AnalyticsOrder.total_price))
            .where(
                AnalyticsOrder.completed_at >= today,
                AnalyticsOrder.status == 'completed'
            )
        )
        daily_revenue = float(daily_result.scalar() or 0)

        # Weekly revenue
        weekly_result = await session.execute(
            select(func.sum(AnalyticsOrder.total_price))
            .where(
                AnalyticsOrder.completed_at >= week_ago,
                AnalyticsOrder.status == 'completed'
            )
        )
        weekly_revenue = float(weekly_result.scalar() or 0)

        # Monthly revenue
        monthly_result = await session.execute(
            select(func.sum(AnalyticsOrder.total_price))
            .where(
                AnalyticsOrder.completed_at >= month_ago,
                AnalyticsOrder.status == 'completed'
            )
        )
        monthly_revenue = float(monthly_result.scalar() or 0)

        return {
            'daily': daily_revenue,
            'weekly': weekly_revenue,
            'monthly': monthly_revenue,
        }


async def get_daily_orders_chart(days: int = 30) -> list[dict]:
    """Get daily order counts for chart."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.date(AnalyticsOrder.created_at).label('date'),
                func.count(AnalyticsOrder.id).label('total'),
                func.count(
                    func.nullif(AnalyticsOrder.status == 'completed', False)
                ).label('completed'),
            )
            .where(AnalyticsOrder.created_at >= cutoff)
            .group_by(func.date(AnalyticsOrder.created_at))
            .order_by(func.date(AnalyticsOrder.created_at))
        )

        return [
            {
                'date': str(row.date),
                'total': row.total,
                'completed': row.completed or 0,
            }
            for row in result
        ]


async def get_daily_revenue_chart(days: int = 30) -> list[dict]:
    """Get daily revenue for chart."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.date(AnalyticsOrder.completed_at).label('date'),
                func.sum(AnalyticsOrder.total_price).label('revenue'),
            )
            .where(
                AnalyticsOrder.completed_at >= cutoff,
                AnalyticsOrder.status == 'completed'
            )
            .group_by(func.date(AnalyticsOrder.completed_at))
            .order_by(func.date(AnalyticsOrder.completed_at))
        )

        return [
            {
                'date': str(row.date),
                'revenue': float(row.revenue or 0),
            }
            for row in result
        ]


async def get_orders_list(
    limit: int = 50,
    offset: int = 0,
    search: str = None,
    worker_id: int = None,
    cemetery_id: int = None,
    date_from: datetime = None,
    date_to: datetime = None,
    status: str = None,
) -> tuple[list[dict], int]:
    """Get filtered orders list with pagination."""
    async with async_session_factory() as session:
        query = select(AnalyticsOrder).order_by(desc(AnalyticsOrder.created_at))
        count_query = select(func.count(AnalyticsOrder.id))

        # Apply filters
        filters = []

        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    AnalyticsOrder.deceased_full_name.ilike(search_pattern),
                    AnalyticsOrder.customer_name.ilike(search_pattern),
                    AnalyticsOrder.cemetery_name.ilike(search_pattern),
                )
            )

        if cemetery_id:
            filters.append(AnalyticsOrder.cemetery_id == cemetery_id)

        if date_from:
            filters.append(AnalyticsOrder.created_at >= date_from)

        if date_to:
            filters.append(AnalyticsOrder.created_at <= date_to)

        if status:
            filters.append(AnalyticsOrder.status == status)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Get total count
        total_result = await session.execute(count_query)
        total_count = total_result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        orders = result.scalars().all()

        # Get acceptance info for each order
        orders_data = []
        for order in orders:
            acceptance_result = await session.execute(
                select(OrderAcceptance).where(OrderAcceptance.order_id == order.id)
            )
            acceptance = acceptance_result.scalar_one_or_none()

            orders_data.append({
                'id': order.id,
                'original_id': order.original_order_id,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'cemetery_name': order.cemetery_name,
                'deceased_full_name': order.deceased_full_name,
                'total_price': float(order.total_price),
                'status': order.status,
                'created_at': order.created_at,
                'accepted_at': order.accepted_at,
                'completed_at': order.completed_at,
                'time_to_accept': format_duration(order.time_to_accept_seconds),
                'worker_username': acceptance.worker_username if acceptance else None,
                'worker_name': acceptance.worker_name if acceptance else None,
                'customer_feedback': acceptance.customer_feedback if acceptance else None,
            })

        return orders_data, total_count


async def get_order_details(order_id: int) -> Optional[dict]:
    """Get detailed order information."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(AnalyticsOrder).where(AnalyticsOrder.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            return None

        # Get acceptance
        acceptance_result = await session.execute(
            select(OrderAcceptance).where(OrderAcceptance.order_id == order.id)
        )
        acceptance = acceptance_result.scalar_one_or_none()

        # Get media
        media_result = await session.execute(
            select(OrderMedia).where(OrderMedia.order_id == order.id)
        )
        media = media_result.scalars().all()

        return {
            'id': order.id,
            'original_id': order.original_order_id,
            'customer_telegram_id': order.customer_telegram_id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'region_name': order.region_name,
            'district_name': order.district_name,
            'cemetery_name': order.cemetery_name,
            'deceased_full_name': order.deceased_full_name,
            'birth_year': order.birth_year,
            'death_year': order.death_year,
            'total_price': float(order.total_price),
            'items_summary': order.items_summary,
            'status': order.status,
            'created_at': order.created_at,
            'posted_to_group_at': order.posted_to_group_at,
            'accepted_at': order.accepted_at,
            'completed_at': order.completed_at,
            'time_to_accept': format_duration(order.time_to_accept_seconds),
            'time_to_accept_seconds': order.time_to_accept_seconds,
            'acceptance': {
                'worker_telegram_id': acceptance.worker_telegram_id,
                'worker_username': acceptance.worker_username,
                'worker_name': acceptance.worker_name,
                'accepted_at': acceptance.accepted_at,
                'photos_submitted_at': acceptance.photos_submitted_at,
                'verified_at': acceptance.verified_at,
                'time_to_complete': format_duration(acceptance.time_to_complete_seconds),
                'is_completed': acceptance.is_completed,
                'customer_feedback': acceptance.customer_feedback,
            } if acceptance else None,
            'media': [
                {
                    'type': m.media_type,
                    'file_id': m.file_id,
                    'uploaded_at': m.uploaded_at,
                }
                for m in media
            ],
        }


async def get_worker_details(telegram_id: int) -> Optional[dict]:
    """Get detailed worker statistics."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(WorkerStats).where(WorkerStats.telegram_id == telegram_id)
        )
        worker = result.scalar_one_or_none()

        if not worker:
            return None

        # Get recent orders
        orders_result = await session.execute(
            select(OrderAcceptance)
            .where(OrderAcceptance.worker_telegram_id == telegram_id)
            .order_by(desc(OrderAcceptance.accepted_at))
            .limit(20)
        )
        recent_acceptances = orders_result.scalars().all()

        return {
            'telegram_id': worker.telegram_id,
            'username': worker.username,
            'display_name': worker.display_name,
            'total_accepted': worker.total_orders_accepted,
            'total_completed': worker.total_orders_completed,
            'total_rejected': worker.total_orders_rejected,
            'total_earnings': float(worker.total_earnings),
            'avg_accept_time': format_duration(worker.avg_accept_time_seconds),
            'avg_accept_seconds': worker.avg_accept_time_seconds,
            'fastest_accept': format_duration(worker.fastest_accept_seconds),
            'positive_feedback': worker.positive_feedback_count,
            'negative_feedback': worker.negative_feedback_count,
            'rating': calculate_worker_rating(worker),
            'first_order_at': worker.first_order_at,
            'last_order_at': worker.last_order_at,
            'recent_orders': [
                {
                    'order_id': a.order_id,
                    'accepted_at': a.accepted_at,
                    'is_completed': a.is_completed,
                    'feedback': a.customer_feedback,
                }
                for a in recent_acceptances
            ],
        }


async def get_cemetery_stats(days: int = 30) -> list[dict]:
    """Get order stats by cemetery."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                AnalyticsOrder.cemetery_name,
                func.count(AnalyticsOrder.id).label('total_orders'),
                func.sum(AnalyticsOrder.total_price).label('total_revenue'),
            )
            .where(
                AnalyticsOrder.created_at >= cutoff,
                AnalyticsOrder.cemetery_name.isnot(None)
            )
            .group_by(AnalyticsOrder.cemetery_name)
            .order_by(desc(func.count(AnalyticsOrder.id)))
            .limit(20)
        )

        return [
            {
                'cemetery_name': row.cemetery_name,
                'total_orders': row.total_orders,
                'total_revenue': float(row.total_revenue or 0),
            }
            for row in result
        ]


# =============================================================================
# Helper Functions
# =============================================================================

def format_duration(seconds: float) -> str:
    """Format seconds into human readable duration."""
    if not seconds or seconds <= 0:
        return "—"

    if seconds < 60:
        return f"{int(seconds)} sek"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes} min {secs} sek"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} soat {minutes} min"


def calculate_worker_rating(worker: WorkerStats) -> float:
    """Calculate worker rating based on performance."""
    if worker.total_orders_completed == 0:
        return 0.0

    # Base score from completion rate
    completion_rate = worker.total_orders_completed / max(worker.total_orders_accepted, 1)

    # Feedback score
    total_feedback = worker.positive_feedback_count + worker.negative_feedback_count
    if total_feedback > 0:
        feedback_rate = worker.positive_feedback_count / total_feedback
    else:
        feedback_rate = 0.5  # Neutral if no feedback

    # Speed bonus (faster is better, max bonus at 1 min)
    speed_bonus = 0
    if worker.avg_accept_time_seconds and worker.avg_accept_time_seconds > 0:
        # 1 minute = 1.0 bonus, 10 minutes = 0.1 bonus
        speed_bonus = min(1.0, 60 / worker.avg_accept_time_seconds)

    # Calculate final rating (0-5 scale)
    rating = (completion_rate * 2) + (feedback_rate * 2) + (speed_bonus * 1)
    return round(min(5.0, rating), 1)


# =============================================================================
# Salary Report Functions
# =============================================================================

async def get_worker_earnings_by_period(
    date_from: datetime,
    date_to: datetime,
) -> list[dict]:
    """
    Get worker earnings for a specific date range.
    Used for weekly/monthly salary reports.
    """
    async with async_session_factory() as session:
        # Get all completed orders in the period with their workers
        result = await session.execute(
            select(
                OrderAcceptance.worker_telegram_id,
                OrderAcceptance.worker_username,
                OrderAcceptance.worker_name,
                func.count(OrderAcceptance.id).label('order_count'),
                func.sum(AnalyticsOrder.total_price).label('total_earnings'),
                func.avg(OrderAcceptance.time_to_accept_seconds).label('avg_accept_time'),
            )
            .join(AnalyticsOrder, OrderAcceptance.order_id == AnalyticsOrder.id)
            .where(
                AnalyticsOrder.completed_at >= date_from,
                AnalyticsOrder.completed_at < date_to,
                AnalyticsOrder.status == 'completed',
                OrderAcceptance.is_completed == True,
            )
            .group_by(
                OrderAcceptance.worker_telegram_id,
                OrderAcceptance.worker_username,
                OrderAcceptance.worker_name,
            )
            .order_by(desc(func.sum(AnalyticsOrder.total_price)))
        )

        workers = []
        for row in result:
            workers.append({
                'telegram_id': row.worker_telegram_id,
                'username': row.worker_username or '',
                'display_name': row.worker_name or '',
                'order_count': row.order_count or 0,
                'total_earnings': float(row.total_earnings or 0),
                'avg_accept_time': format_duration(row.avg_accept_time),
            })

        return workers


async def get_period_orders_detail(
    date_from: datetime,
    date_to: datetime,
    worker_telegram_id: int = None,
) -> list[dict]:
    """
    Get detailed order list for a period, optionally filtered by worker.
    """
    async with async_session_factory() as session:
        query = (
            select(
                AnalyticsOrder.id,
                AnalyticsOrder.original_order_id,
                AnalyticsOrder.cemetery_name,
                AnalyticsOrder.deceased_full_name,
                AnalyticsOrder.total_price,
                AnalyticsOrder.completed_at,
                OrderAcceptance.worker_telegram_id,
                OrderAcceptance.worker_username,
                OrderAcceptance.worker_name,
            )
            .join(OrderAcceptance, OrderAcceptance.order_id == AnalyticsOrder.id)
            .where(
                AnalyticsOrder.completed_at >= date_from,
                AnalyticsOrder.completed_at < date_to,
                AnalyticsOrder.status == 'completed',
            )
            .order_by(AnalyticsOrder.completed_at)
        )

        if worker_telegram_id:
            query = query.where(OrderAcceptance.worker_telegram_id == worker_telegram_id)

        result = await session.execute(query)

        return [
            {
                'id': row.id,
                'original_id': row.original_order_id,
                'cemetery_name': row.cemetery_name,
                'deceased_full_name': row.deceased_full_name,
                'total_price': float(row.total_price or 0),
                'completed_at': row.completed_at,
                'worker_telegram_id': row.worker_telegram_id,
                'worker_username': row.worker_username,
                'worker_name': row.worker_name,
            }
            for row in result
        ]


async def get_period_summary(date_from: datetime, date_to: datetime) -> dict:
    """Get summary statistics for a period."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.count(AnalyticsOrder.id).label('total_orders'),
                func.sum(AnalyticsOrder.total_price).label('total_revenue'),
                func.count(distinct(OrderAcceptance.worker_telegram_id)).label('active_workers'),
            )
            .join(OrderAcceptance, OrderAcceptance.order_id == AnalyticsOrder.id, isouter=True)
            .where(
                AnalyticsOrder.completed_at >= date_from,
                AnalyticsOrder.completed_at < date_to,
                AnalyticsOrder.status == 'completed',
            )
        )
        row = result.one()

        return {
            'total_orders': row.total_orders or 0,
            'total_revenue': float(row.total_revenue or 0),
            'active_workers': row.active_workers or 0,
        }

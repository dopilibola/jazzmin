"""
Financial calculation service for the grave care platform.
Handles pricing, commission splits, and revenue tracking.
All money operations use Decimal for precision.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, func, and_, or_, case, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db import async_session_factory
from bot.database.finance_models import (
    ServiceCatalog,
    CemeteryPricing,
    ServicePricingRule,
    OrderFinancial,
    WorkerEarnings,
    DailyRevenue,
    ORDER_FIN_STATUS_PENDING,
    ORDER_FIN_STATUS_PAID,
    ORDER_FIN_STATUS_COMPLETED,
    ORDER_FIN_STATUS_RETURNED,
    ORDER_FIN_STATUS_CANCELED,
)

logger = logging.getLogger(__name__)

# Default commission percentages
DEFAULT_PLATFORM_PERCENT = Decimal("30.00")
DEFAULT_WORKER_PERCENT = Decimal("70.00")


def round_money(value: Decimal) -> Decimal:
    """Round money to 2 decimal places."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# -----------------------------------------------------------------------------
# Price Calculation
# -----------------------------------------------------------------------------


async def calculate_service_price(
    session: AsyncSession,
    service_id: int,
    cemetery_id: Optional[int] = None,
) -> dict:
    """
    Calculate final price for a service at a specific cemetery.
    Returns pricing details including commission split.

    Logic:
    1. If custom_price exists in pricing rule -> use it
    2. Else -> base_price * cemetery_multiplier
    """
    # Get service
    service = await session.get(ServiceCatalog, service_id)
    if not service:
        raise ValueError(f"Service {service_id} not found")

    base_price = Decimal(str(service.base_price))
    multiplier = Decimal("1.00")
    custom_price = None
    platform_percent = DEFAULT_PLATFORM_PERCENT
    worker_percent = DEFAULT_WORKER_PERCENT

    # Get cemetery multiplier if provided
    cemetery_name = "—"
    if cemetery_id:
        cemetery = await session.get(CemeteryPricing, cemetery_id)
        if cemetery:
            multiplier = Decimal(str(cemetery.price_multiplier))
            cemetery_name = cemetery.name

    # Check for specific pricing rule
    query = select(ServicePricingRule).where(
        ServicePricingRule.service_id == service_id,
        ServicePricingRule.is_active == True,
    )

    # Prefer cemetery-specific rule, fallback to general rule
    if cemetery_id:
        query = query.where(
            or_(
                ServicePricingRule.cemetery_id == cemetery_id,
                ServicePricingRule.cemetery_id == None,
            )
        ).order_by(
            # Cemetery-specific rules first
            case((ServicePricingRule.cemetery_id != None, 0), else_=1)
        )
    else:
        query = query.where(ServicePricingRule.cemetery_id == None)

    result = await session.execute(query)
    pricing_rule = result.scalars().first()

    if pricing_rule:
        if pricing_rule.custom_price is not None:
            custom_price = Decimal(str(pricing_rule.custom_price))
        platform_percent = Decimal(str(pricing_rule.platform_percent))
        worker_percent = Decimal(str(pricing_rule.worker_percent))

    # Calculate final price
    if custom_price is not None:
        final_price = custom_price
    else:
        final_price = round_money(base_price * multiplier)

    # Calculate earnings split
    platform_earning = round_money(final_price * platform_percent / Decimal("100"))
    worker_earning = round_money(final_price * worker_percent / Decimal("100"))

    return {
        "service_id": service_id,
        "service_name": service.name,
        "cemetery_id": cemetery_id,
        "cemetery_name": cemetery_name,
        "base_price": base_price,
        "multiplier": multiplier,
        "custom_price": custom_price,
        "final_price": final_price,
        "platform_percent": platform_percent,
        "worker_percent": worker_percent,
        "platform_earning": platform_earning,
        "worker_earning": worker_earning,
    }


async def get_service_price(service_id: int, cemetery_id: Optional[int] = None) -> dict:
    """Public wrapper for price calculation."""
    async with async_session_factory() as session:
        return await calculate_service_price(session, service_id, cemetery_id)


# -----------------------------------------------------------------------------
# Order Financial Management
# -----------------------------------------------------------------------------


async def create_order_financial(
    session: AsyncSession,
    order_id: int,
    service_id: int,
    cemetery_id: Optional[int],
    user_id: Optional[int] = None,
    user_telegram_id: Optional[int] = None,
) -> OrderFinancial:
    """Create financial record for a new order."""
    pricing = await calculate_service_price(session, service_id, cemetery_id)

    order_fin = OrderFinancial(
        order_id=order_id,
        user_id=user_id,
        user_telegram_id=user_telegram_id,
        service_id=service_id,
        service_name=pricing["service_name"],
        cemetery_id=cemetery_id,
        cemetery_name=pricing["cemetery_name"],
        base_price=pricing["base_price"],
        price_multiplier=pricing["multiplier"],
        final_price=pricing["final_price"],
        platform_percent=pricing["platform_percent"],
        worker_percent=pricing["worker_percent"],
        platform_earning=pricing["platform_earning"],
        worker_earning=pricing["worker_earning"],
        status=ORDER_FIN_STATUS_PENDING,
    )

    session.add(order_fin)
    await session.flush()
    logger.info(f"Created order financial #{order_fin.id} for order #{order_id}")
    return order_fin


async def create_order_financial_simple(
    session: AsyncSession,
    order_id: int,
    service_name: str,
    final_price: int,
    user_id: Optional[int] = None,
    user_telegram_id: Optional[int] = None,
    cemetery_name: Optional[str] = None,
    platform_percent: Decimal = DEFAULT_PLATFORM_PERCENT,
    worker_percent: Decimal = DEFAULT_WORKER_PERCENT,
) -> OrderFinancial:
    """Create financial record directly from order data (without ServiceCatalog).

    Use this when the order is created from Django services that don't have
    corresponding ServiceCatalog entries.
    """
    final_price_decimal = Decimal(str(final_price))

    # Calculate earnings split
    platform_earning = round_money(final_price_decimal * platform_percent / Decimal("100"))
    worker_earning = round_money(final_price_decimal * worker_percent / Decimal("100"))

    order_fin = OrderFinancial(
        order_id=order_id,
        user_id=user_id,
        user_telegram_id=user_telegram_id,
        service_id=None,  # No ServiceCatalog reference
        service_name=service_name,
        cemetery_id=None,  # No CemeteryPricing reference
        cemetery_name=cemetery_name or "—",
        base_price=final_price_decimal,
        price_multiplier=Decimal("1.00"),
        final_price=final_price_decimal,
        platform_percent=platform_percent,
        worker_percent=worker_percent,
        platform_earning=platform_earning,
        worker_earning=worker_earning,
        status=ORDER_FIN_STATUS_PENDING,
    )

    session.add(order_fin)
    await session.flush()
    logger.info(f"Created simple order financial #{order_fin.id} for order #{order_id}")
    return order_fin


async def create_financial_for_order(order_id: int) -> Optional[OrderFinancial]:
    """Create financial record for an existing order (public wrapper).

    Fetches order from DB and creates financial record.
    Returns None if order not found or financial already exists.
    """
    from bot.database.models import Order

    async with async_session_factory() as session:
        # Check if financial record already exists
        result = await session.execute(
            select(OrderFinancial).where(OrderFinancial.order_id == order_id)
        )
        if result.scalars().first():
            logger.debug(f"Financial record already exists for order #{order_id}")
            return None

        # Get order
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalars().first()
        if not order:
            return None

        # Get service name from items
        service_name = "Xizmat"
        cemetery_name = "—"

        if order.items:
            service_names = [item.title for item in order.items if item.item_type == "service"]
            if service_names:
                service_name = ", ".join(service_names)

        if order.cemetery:
            cemetery_name = order.cemetery.name

        # Get user telegram_id
        user_telegram_id = None
        if order.user:
            user_telegram_id = order.user.telegram_id

        order_fin = await create_order_financial_simple(
            session,
            order_id=order.id,
            service_name=service_name,
            final_price=order.total_price,
            user_id=order.user_id,
            user_telegram_id=user_telegram_id,
            cemetery_name=cemetery_name,
        )

        await session.commit()
        return order_fin


async def assign_worker_to_order(
    session: AsyncSession,
    order_id: int,
    worker_telegram_id: int,
    worker_username: Optional[str] = None,
) -> Optional[OrderFinancial]:
    """Assign worker to order financial record."""
    result = await session.execute(
        select(OrderFinancial).where(OrderFinancial.order_id == order_id)
    )
    order_fin = result.scalars().first()

    if order_fin:
        order_fin.worker_telegram_id = worker_telegram_id
        order_fin.worker_username = worker_username
        order_fin.status = ORDER_FIN_STATUS_PAID
        await session.flush()
        logger.info(f"Assigned worker @{worker_username} to order #{order_id}")

    return order_fin


async def complete_order_financial(
    session: AsyncSession,
    order_id: int,
) -> Optional[OrderFinancial]:
    """Mark order as completed and finalize earnings."""
    result = await session.execute(
        select(OrderFinancial).where(OrderFinancial.order_id == order_id)
    )
    order_fin = result.scalars().first()

    if order_fin:
        order_fin.status = ORDER_FIN_STATUS_COMPLETED
        order_fin.completed_at = datetime.utcnow()
        await session.flush()

        # Update worker earnings
        await update_worker_earnings(
            session,
            order_fin.worker_telegram_id,
            order_fin.worker_username,
            order_fin.worker_earning,
            completed=True,
        )

        logger.info(f"Completed order #{order_id}, worker earns {order_fin.worker_earning}")

    return order_fin


async def return_order_financial(
    session: AsyncSession,
    order_id: int,
) -> Optional[OrderFinancial]:
    """Mark order as returned (needs rework)."""
    result = await session.execute(
        select(OrderFinancial).where(OrderFinancial.order_id == order_id)
    )
    order_fin = result.scalars().first()

    if order_fin:
        old_status = order_fin.status
        order_fin.status = ORDER_FIN_STATUS_RETURNED

        # If was completed, reverse worker earnings
        if old_status == ORDER_FIN_STATUS_COMPLETED and order_fin.worker_telegram_id:
            await update_worker_earnings(
                session,
                order_fin.worker_telegram_id,
                order_fin.worker_username,
                -order_fin.worker_earning,  # Negative to reverse
                returned=True,
            )

        await session.flush()
        logger.info(f"Returned order #{order_id}")

    return order_fin


async def cancel_order_financial(
    session: AsyncSession,
    order_id: int,
) -> Optional[OrderFinancial]:
    """Mark order as canceled - excluded from revenue."""
    result = await session.execute(
        select(OrderFinancial).where(OrderFinancial.order_id == order_id)
    )
    order_fin = result.scalars().first()

    if order_fin:
        old_status = order_fin.status
        order_fin.status = ORDER_FIN_STATUS_CANCELED

        # If was completed, reverse worker earnings
        if old_status == ORDER_FIN_STATUS_COMPLETED and order_fin.worker_telegram_id:
            await update_worker_earnings(
                session,
                order_fin.worker_telegram_id,
                order_fin.worker_username,
                -order_fin.worker_earning,
                canceled=True,
            )

        await session.flush()
        logger.info(f"Canceled order #{order_id}")

    return order_fin


# -----------------------------------------------------------------------------
# Worker Earnings
# -----------------------------------------------------------------------------


async def update_worker_earnings(
    session: AsyncSession,
    worker_telegram_id: int,
    worker_username: Optional[str],
    amount: Decimal,
    completed: bool = False,
    returned: bool = False,
    canceled: bool = False,
) -> WorkerEarnings:
    """Update worker's earnings summary."""
    result = await session.execute(
        select(WorkerEarnings).where(
            WorkerEarnings.worker_telegram_id == worker_telegram_id
        )
    )
    worker = result.scalars().first()

    if not worker:
        worker = WorkerEarnings(
            worker_telegram_id=worker_telegram_id,
            worker_username=worker_username,
        )
        session.add(worker)

    # Update username if provided
    if worker_username:
        worker.worker_username = worker_username

    # Update counts and earnings
    if completed:
        worker.total_orders += 1
        worker.completed_orders += 1
        worker.total_earned += amount
        worker.last_order_at = datetime.utcnow()
    elif returned:
        worker.returned_orders += 1
        worker.total_earned += amount  # amount is negative
    elif canceled:
        worker.canceled_orders += 1
        worker.total_earned += amount  # amount is negative

    await session.flush()
    return worker


async def get_worker_stats(worker_telegram_id: int) -> dict:
    """Get detailed worker statistics."""
    async with async_session_factory() as session:
        # Get summary
        result = await session.execute(
            select(WorkerEarnings).where(
                WorkerEarnings.worker_telegram_id == worker_telegram_id
            )
        )
        worker = result.scalars().first()

        if not worker:
            return {
                "found": False,
                "worker_telegram_id": worker_telegram_id,
            }

        # Earnings by service
        result = await session.execute(
            select(
                OrderFinancial.service_name,
                func.count(OrderFinancial.id).label("count"),
                func.sum(OrderFinancial.worker_earning).label("total"),
            ).where(
                OrderFinancial.worker_telegram_id == worker_telegram_id,
                OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED,
            ).group_by(OrderFinancial.service_name)
        )
        by_service = [{"name": r.service_name, "count": r.count, "total": r.total or 0} for r in result.fetchall()]

        # Earnings by cemetery
        result = await session.execute(
            select(
                OrderFinancial.cemetery_name,
                func.count(OrderFinancial.id).label("count"),
                func.sum(OrderFinancial.worker_earning).label("total"),
            ).where(
                OrderFinancial.worker_telegram_id == worker_telegram_id,
                OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED,
            ).group_by(OrderFinancial.cemetery_name)
        )
        by_cemetery = [{"name": r.cemetery_name, "count": r.count, "total": r.total or 0} for r in result.fetchall()]

        return {
            "found": True,
            "worker_telegram_id": worker_telegram_id,
            "username": worker.worker_username,
            "total_orders": worker.total_orders,
            "completed_orders": worker.completed_orders,
            "returned_orders": worker.returned_orders,
            "canceled_orders": worker.canceled_orders,
            "total_earned": worker.total_earned,
            "last_order_at": worker.last_order_at,
            "by_service": by_service,
            "by_cemetery": by_cemetery,
        }


# -----------------------------------------------------------------------------
# Dashboard Statistics
# -----------------------------------------------------------------------------


async def get_financial_dashboard(
    days: int = 30,
    cemetery_id: Optional[int] = None,
    service_id: Optional[int] = None,
) -> dict:
    """Generate financial dashboard data with optional filters."""
    async with async_session_factory() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Base query filters
        filters = [OrderFinancial.created_at >= cutoff]
        if cemetery_id:
            filters.append(OrderFinancial.cemetery_id == cemetery_id)
        if service_id:
            filters.append(OrderFinancial.service_id == service_id)

        # Total revenue (completed orders only)
        result = await session.execute(
            select(
                func.count(OrderFinancial.id).label("total_orders"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, OrderFinancial.final_price),
                        else_=Decimal("0"),
                    )
                ).label("total_revenue"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, OrderFinancial.platform_earning),
                        else_=Decimal("0"),
                    )
                ).label("platform_revenue"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, OrderFinancial.worker_earning),
                        else_=Decimal("0"),
                    )
                ).label("worker_payouts"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, 1),
                        else_=0,
                    )
                ).label("completed_count"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_RETURNED, 1),
                        else_=0,
                    )
                ).label("returned_count"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_CANCELED, 1),
                        else_=0,
                    )
                ).label("canceled_count"),
            ).where(*filters)
        )
        row = result.fetchone()

        total_orders = row.total_orders or 0
        total_revenue = row.total_revenue or Decimal("0")
        platform_revenue = row.platform_revenue or Decimal("0")
        worker_payouts = row.worker_payouts or Decimal("0")
        completed_count = row.completed_count or 0
        returned_count = row.returned_count or 0
        canceled_count = row.canceled_count or 0

        # Profit margin
        profit_margin = Decimal("0")
        if total_revenue > 0:
            profit_margin = round_money(platform_revenue / total_revenue * 100)

        # Top workers
        result = await session.execute(
            select(
                OrderFinancial.worker_username,
                OrderFinancial.worker_telegram_id,
                func.sum(OrderFinancial.worker_earning).label("total"),
                func.count(OrderFinancial.id).label("orders"),
            ).where(
                *filters,
                OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED,
                OrderFinancial.worker_telegram_id != None,
            ).group_by(
                OrderFinancial.worker_username,
                OrderFinancial.worker_telegram_id,
            ).order_by(func.sum(OrderFinancial.worker_earning).desc()).limit(10)
        )
        top_workers = [
            {
                "username": r.worker_username or "Unknown",
                "telegram_id": r.worker_telegram_id,
                "total": r.total or 0,
                "orders": r.orders,
            }
            for r in result.fetchall()
        ]

        # Cemetery stats
        result = await session.execute(
            select(
                OrderFinancial.cemetery_name,
                OrderFinancial.cemetery_id,
                func.sum(OrderFinancial.final_price).label("total"),
                func.count(OrderFinancial.id).label("orders"),
            ).where(
                *filters,
                OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED,
            ).group_by(
                OrderFinancial.cemetery_name,
                OrderFinancial.cemetery_id,
            ).order_by(func.sum(OrderFinancial.final_price).desc()).limit(10)
        )
        cemetery_stats = [
            {
                "name": r.cemetery_name,
                "id": r.cemetery_id,
                "total": r.total or 0,
                "orders": r.orders,
            }
            for r in result.fetchall()
        ]

        # Service stats
        result = await session.execute(
            select(
                OrderFinancial.service_name,
                OrderFinancial.service_id,
                func.sum(OrderFinancial.final_price).label("total"),
                func.count(OrderFinancial.id).label("orders"),
            ).where(
                *filters,
                OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED,
            ).group_by(
                OrderFinancial.service_name,
                OrderFinancial.service_id,
            ).order_by(func.sum(OrderFinancial.final_price).desc()).limit(10)
        )
        service_stats = [
            {
                "name": r.service_name,
                "id": r.service_id,
                "total": r.total or 0,
                "orders": r.orders,
            }
            for r in result.fetchall()
        ]

        return {
            "period_days": days,
            "total_orders": total_orders,
            "completed_orders": completed_count,
            "returned_orders": returned_count,
            "canceled_orders": canceled_count,
            "total_revenue": total_revenue,
            "platform_revenue": platform_revenue,
            "worker_payouts": worker_payouts,
            "profit_margin": profit_margin,
            "top_workers": top_workers,
            "cemetery_stats": cemetery_stats,
            "service_stats": service_stats,
        }


# -----------------------------------------------------------------------------
# Service & Cemetery Management
# -----------------------------------------------------------------------------


async def create_service(
    name: str,
    base_price: Decimal,
    description: Optional[str] = None,
) -> ServiceCatalog:
    """Create a new service."""
    async with async_session_factory() as session:
        service = ServiceCatalog(
            name=name,
            base_price=base_price,
            description=description,
        )
        session.add(service)
        await session.commit()
        return service


async def update_service(
    service_id: int,
    name: Optional[str] = None,
    base_price: Optional[Decimal] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[ServiceCatalog]:
    """Update a service."""
    async with async_session_factory() as session:
        service = await session.get(ServiceCatalog, service_id)
        if service:
            if name is not None:
                service.name = name
            if base_price is not None:
                service.base_price = base_price
            if description is not None:
                service.description = description
            if is_active is not None:
                service.is_active = is_active
            await session.commit()
        return service


async def get_all_services() -> list[ServiceCatalog]:
    """Get all active services."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ServiceCatalog).where(ServiceCatalog.is_active == True).order_by(ServiceCatalog.name)
        )
        return list(result.scalars().all())


async def create_cemetery(
    name: str,
    price_multiplier: Decimal = Decimal("1.00"),
    district: Optional[str] = None,
    region: Optional[str] = None,
) -> CemeteryPricing:
    """Create a new cemetery pricing entry."""
    async with async_session_factory() as session:
        cemetery = CemeteryPricing(
            name=name,
            price_multiplier=price_multiplier,
            district=district,
            region=region,
        )
        session.add(cemetery)
        await session.commit()
        return cemetery


async def update_cemetery(
    cemetery_id: int,
    name: Optional[str] = None,
    price_multiplier: Optional[Decimal] = None,
    district: Optional[str] = None,
    region: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[CemeteryPricing]:
    """Update a cemetery."""
    async with async_session_factory() as session:
        cemetery = await session.get(CemeteryPricing, cemetery_id)
        if cemetery:
            if name is not None:
                cemetery.name = name
            if price_multiplier is not None:
                cemetery.price_multiplier = price_multiplier
            if district is not None:
                cemetery.district = district
            if region is not None:
                cemetery.region = region
            if is_active is not None:
                cemetery.is_active = is_active
            await session.commit()
        return cemetery


async def get_all_cemeteries() -> list[CemeteryPricing]:
    """Get all active cemeteries."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(CemeteryPricing).where(CemeteryPricing.is_active == True).order_by(CemeteryPricing.name)
        )
        return list(result.scalars().all())


async def set_pricing_rule(
    service_id: int,
    cemetery_id: Optional[int] = None,
    custom_price: Optional[Decimal] = None,
    platform_percent: Decimal = DEFAULT_PLATFORM_PERCENT,
    worker_percent: Decimal = DEFAULT_WORKER_PERCENT,
) -> ServicePricingRule:
    """Set or update pricing rule for service/cemetery combination."""
    async with async_session_factory() as session:
        # Check for existing rule
        query = select(ServicePricingRule).where(
            ServicePricingRule.service_id == service_id,
        )
        if cemetery_id:
            query = query.where(ServicePricingRule.cemetery_id == cemetery_id)
        else:
            query = query.where(ServicePricingRule.cemetery_id == None)

        result = await session.execute(query)
        rule = result.scalars().first()

        if rule:
            rule.custom_price = custom_price
            rule.platform_percent = platform_percent
            rule.worker_percent = worker_percent
            rule.is_active = True
        else:
            rule = ServicePricingRule(
                service_id=service_id,
                cemetery_id=cemetery_id,
                custom_price=custom_price,
                platform_percent=platform_percent,
                worker_percent=worker_percent,
            )
            session.add(rule)

        await session.commit()
        return rule


async def get_pricing_rules(service_id: Optional[int] = None) -> list[ServicePricingRule]:
    """Get all pricing rules, optionally filtered by service."""
    async with async_session_factory() as session:
        query = select(ServicePricingRule).where(ServicePricingRule.is_active == True)
        if service_id:
            query = query.where(ServicePricingRule.service_id == service_id)
        result = await session.execute(query)
        return list(result.scalars().all())


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def format_money(amount: Decimal, currency: str = "so'm") -> str:
    """Format money for display."""
    # Format with thousands separator
    formatted = f"{int(amount):,}".replace(",", " ")
    return f"{formatted} {currency}"


async def recalculate_daily_revenue(date: datetime) -> DailyRevenue:
    """Recalculate daily revenue for a specific date."""
    async with async_session_factory() as session:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await session.execute(
            select(
                func.count(OrderFinancial.id).label("total_orders"),
                func.sum(
                    case((OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, 1), else_=0)
                ).label("completed"),
                func.sum(
                    case((OrderFinancial.status == ORDER_FIN_STATUS_RETURNED, 1), else_=0)
                ).label("returned"),
                func.sum(
                    case((OrderFinancial.status == ORDER_FIN_STATUS_CANCELED, 1), else_=0)
                ).label("canceled"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, OrderFinancial.final_price),
                        else_=Decimal("0"),
                    )
                ).label("revenue"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, OrderFinancial.platform_earning),
                        else_=Decimal("0"),
                    )
                ).label("platform"),
                func.sum(
                    case(
                        (OrderFinancial.status == ORDER_FIN_STATUS_COMPLETED, OrderFinancial.worker_earning),
                        else_=Decimal("0"),
                    )
                ).label("worker"),
            ).where(
                OrderFinancial.created_at >= start,
                OrderFinancial.created_at < end,
            )
        )
        row = result.fetchone()

        # Upsert daily revenue
        result = await session.execute(
            select(DailyRevenue).where(DailyRevenue.date == start)
        )
        daily = result.scalars().first()

        if not daily:
            daily = DailyRevenue(date=start)
            session.add(daily)

        daily.total_orders = row.total_orders or 0
        daily.completed_orders = row.completed or 0
        daily.returned_orders = row.returned or 0
        daily.canceled_orders = row.canceled or 0
        daily.total_revenue = row.revenue or Decimal("0")
        daily.platform_revenue = row.platform or Decimal("0")
        daily.worker_payouts = row.worker or Decimal("0")

        await session.commit()
        return daily

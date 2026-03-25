"""
Analytics tracking system for the Telegram bot.
Tracks user events, funnel drop-offs, and generates statistics.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db import async_session_factory

logger = logging.getLogger(__name__)

# Event types for tracking
EVENT_START = "start"
EVENT_LANGUAGE_SELECT = "language_select"
EVENT_REGISTRATION_NAME = "registration_name"
EVENT_REGISTRATION_COMPLETE = "registration_complete"
EVENT_GRAVE_REGION = "grave_region"
EVENT_GRAVE_DISTRICT = "grave_district"
EVENT_GRAVE_CEMETERY = "grave_cemetery"
EVENT_GRAVE_DECEASED = "grave_deceased"
EVENT_GRAVE_BIRTH = "grave_birth"
EVENT_GRAVE_DEATH = "grave_death"
EVENT_GRAVE_RELATIONSHIP = "grave_relationship"
EVENT_GRAVE_COMPLETE = "grave_complete"
EVENT_SERVICES_VIEW = "services_view"
EVENT_SERVICE_ORDER = "service_order"
EVENT_FLOWERS_VIEW = "flowers_view"
EVENT_FLOWER_ORDER = "flower_order"
EVENT_CART_VIEW = "cart_view"
EVENT_CHECKOUT_START = "checkout_start"
EVENT_CHECKOUT_COMPLETE = "checkout_complete"
EVENT_PAYMENT_METHOD = "payment_method"
EVENT_PAYMENT_RECEIPT = "payment_receipt"
EVENT_PAYMENT_CONFIRMED = "payment_confirmed"
EVENT_PROFILE_VIEW = "profile_view"
EVENT_SUPPORT = "support"

# Funnel stages for analysis
REGISTRATION_FUNNEL = [
    EVENT_START,
    EVENT_LANGUAGE_SELECT,
    EVENT_REGISTRATION_NAME,
    EVENT_REGISTRATION_COMPLETE,
]

GRAVE_FUNNEL = [
    EVENT_GRAVE_REGION,
    EVENT_GRAVE_DISTRICT,
    EVENT_GRAVE_CEMETERY,
    EVENT_GRAVE_DECEASED,
    EVENT_GRAVE_BIRTH,
    EVENT_GRAVE_DEATH,
    EVENT_GRAVE_RELATIONSHIP,
    EVENT_GRAVE_COMPLETE,
]

ORDER_FUNNEL = [
    EVENT_SERVICE_ORDER,
    EVENT_CHECKOUT_START,
    EVENT_CHECKOUT_COMPLETE,
    EVENT_PAYMENT_METHOD,
    EVENT_PAYMENT_RECEIPT,
    EVENT_PAYMENT_CONFIRMED,
]

# In-memory storage for simplicity (can be moved to DB later)
_events: list[dict] = []


async def track_event(
    telegram_id: int,
    event_type: str,
    metadata: Optional[dict] = None
) -> None:
    """Track a user event."""
    event = {
        "telegram_id": telegram_id,
        "event_type": event_type,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {},
    }
    _events.append(event)

    # Keep only last 100k events in memory
    if len(_events) > 100000:
        _events.pop(0)

    logger.debug(f"Event tracked: {event_type} for user {telegram_id}")


def get_events_since(hours: int = 24) -> list[dict]:
    """Get events from the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return [e for e in _events if e["timestamp"] >= cutoff]


def get_unique_users(events: list[dict]) -> set[int]:
    """Get unique user IDs from events."""
    return {e["telegram_id"] for e in events}


def count_events_by_type(events: list[dict]) -> dict[str, int]:
    """Count events by type."""
    counts = defaultdict(int)
    for e in events:
        counts[e["event_type"]] += 1
    return dict(counts)


def count_users_by_event(events: list[dict]) -> dict[str, int]:
    """Count unique users per event type."""
    users_by_event = defaultdict(set)
    for e in events:
        users_by_event[e["event_type"]].add(e["telegram_id"])
    return {k: len(v) for k, v in users_by_event.items()}


def calculate_funnel(events: list[dict], funnel_stages: list[str]) -> list[dict]:
    """
    Calculate funnel drop-off for given stages.
    Returns list of {stage, users, percentage, drop_off}
    """
    users_by_stage = defaultdict(set)
    for e in events:
        if e["event_type"] in funnel_stages:
            users_by_stage[e["event_type"]].add(e["telegram_id"])

    result = []
    prev_users = None

    for stage in funnel_stages:
        current_users = len(users_by_stage.get(stage, set()))

        if prev_users is None:
            percentage = 100.0
            drop_off = 0.0
        elif prev_users == 0:
            percentage = 0.0
            drop_off = 0.0
        else:
            percentage = (current_users / prev_users) * 100
            drop_off = 100 - percentage

        result.append({
            "stage": stage,
            "users": current_users,
            "percentage": round(percentage, 1),
            "drop_off": round(drop_off, 1),
        })

        if current_users > 0:
            prev_users = current_users

    return result


def get_hourly_activity(events: list[dict]) -> dict[int, int]:
    """Get event count by hour of day."""
    hourly = defaultdict(int)
    for e in events:
        hour = e["timestamp"].hour
        hourly[hour] += 1
    return dict(hourly)


def get_daily_users(events: list[dict], days: int = 7) -> list[dict]:
    """Get unique users per day for last N days."""
    daily = defaultdict(set)
    cutoff = datetime.utcnow() - timedelta(days=days)

    for e in events:
        if e["timestamp"] >= cutoff:
            date_str = e["timestamp"].strftime("%Y-%m-%d")
            daily[date_str].add(e["telegram_id"])

    result = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
        result.append({
            "date": date,
            "users": len(daily.get(date, set())),
        })

    return result


async def generate_analytics_report(hours: int = 24) -> str:
    """Generate full analytics report text."""
    events = get_events_since(hours)

    if not events:
        return "📊 Analitika\n\nSo'nggi 24 soatda hech qanday ma'lumot yo'q."

    unique_users = get_unique_users(events)
    event_counts = count_events_by_type(events)
    users_by_event = count_users_by_event(events)

    # Registration funnel
    reg_funnel = calculate_funnel(events, REGISTRATION_FUNNEL)

    # Grave funnel
    grave_funnel = calculate_funnel(events, GRAVE_FUNNEL)

    # Order funnel
    order_funnel = calculate_funnel(events, ORDER_FUNNEL)

    # Daily stats
    daily_users = get_daily_users(events, 7)

    # Build report
    lines = [
        "📊 <b>BOT ANALITIKASI</b>",
        f"📅 So'nggi {hours} soat",
        "",
        f"👥 <b>Umumiy statistika:</b>",
        f"   • Jami eventlar: {len(events)}",
        f"   • Unikal foydalanuvchilar: {len(unique_users)}",
        "",
    ]

    # Event breakdown
    lines.append("📈 <b>Event statistikasi:</b>")
    event_labels = {
        EVENT_START: "/start",
        EVENT_LANGUAGE_SELECT: "Til tanlash",
        EVENT_REGISTRATION_NAME: "Ism kiritish",
        EVENT_REGISTRATION_COMPLETE: "Ro'yxatdan o'tish",
        EVENT_GRAVE_REGION: "Viloyat tanlash",
        EVENT_GRAVE_DISTRICT: "Tuman tanlash",
        EVENT_GRAVE_CEMETERY: "Qabriston tanlash",
        EVENT_GRAVE_DECEASED: "Marhum ismi",
        EVENT_GRAVE_COMPLETE: "Qabr saqlash",
        EVENT_SERVICES_VIEW: "Xizmatlar ko'rish",
        EVENT_SERVICE_ORDER: "Xizmat buyurtma",
        EVENT_FLOWERS_VIEW: "Gullar ko'rish",
        EVENT_FLOWER_ORDER: "Gul buyurtma",
        EVENT_PAYMENT_RECEIPT: "To'lov cheki",
        EVENT_PAYMENT_CONFIRMED: "To'lov tasdiqlandi",
    }

    for event_type, label in event_labels.items():
        count = event_counts.get(event_type, 0)
        users = users_by_event.get(event_type, 0)
        if count > 0:
            lines.append(f"   • {label}: {count} ({users} user)")

    lines.append("")

    # Registration funnel
    lines.append("🔄 <b>Ro'yxatdan o'tish funneli:</b>")
    stage_labels = {
        EVENT_START: "/start",
        EVENT_LANGUAGE_SELECT: "Til",
        EVENT_REGISTRATION_NAME: "Ism",
        EVENT_REGISTRATION_COMPLETE: "Tugadi",
    }
    for item in reg_funnel:
        label = stage_labels.get(item["stage"], item["stage"])
        if item["users"] > 0:
            drop = f" (-{item['drop_off']}%)" if item["drop_off"] > 0 else ""
            lines.append(f"   {label}: {item['users']} user ({item['percentage']}%){drop}")

    lines.append("")

    # Grave funnel
    lines.append("🪦 <b>Qabr qo'shish funneli:</b>")
    stage_labels = {
        EVENT_GRAVE_REGION: "Viloyat",
        EVENT_GRAVE_DISTRICT: "Tuman",
        EVENT_GRAVE_CEMETERY: "Qabriston",
        EVENT_GRAVE_DECEASED: "Marhum",
        EVENT_GRAVE_BIRTH: "Tug'ilgan",
        EVENT_GRAVE_DEATH: "Vafot",
        EVENT_GRAVE_RELATIONSHIP: "Qarindosh",
        EVENT_GRAVE_COMPLETE: "Saqlandi",
    }
    for item in grave_funnel:
        label = stage_labels.get(item["stage"], item["stage"])
        if item["users"] > 0:
            drop = f" (-{item['drop_off']}%)" if item["drop_off"] > 0 else ""
            lines.append(f"   {label}: {item['users']} user ({item['percentage']}%){drop}")

    lines.append("")

    # Order funnel
    lines.append("💳 <b>Buyurtma funneli:</b>")
    stage_labels = {
        EVENT_SERVICE_ORDER: "Buyurtma",
        EVENT_CHECKOUT_START: "Checkout",
        EVENT_CHECKOUT_COMPLETE: "Tasdiqlash",
        EVENT_PAYMENT_METHOD: "To'lov usuli",
        EVENT_PAYMENT_RECEIPT: "Chek yuklash",
        EVENT_PAYMENT_CONFIRMED: "Tasdiqlandi",
    }
    for item in order_funnel:
        label = stage_labels.get(item["stage"], item["stage"])
        if item["users"] > 0:
            drop = f" (-{item['drop_off']}%)" if item["drop_off"] > 0 else ""
            lines.append(f"   {label}: {item['users']} user ({item['percentage']}%){drop}")

    lines.append("")

    # Daily trend
    lines.append("📅 <b>Kunlik trend (7 kun):</b>")
    for day in daily_users:
        lines.append(f"   {day['date']}: {day['users']} user")

    # Problem areas
    lines.append("")
    lines.append("⚠️ <b>Muammoli joylar:</b>")

    problems = []
    for funnel in [reg_funnel, grave_funnel, order_funnel]:
        for item in funnel:
            if item["drop_off"] > 30:
                stage_name = stage_labels.get(item["stage"], item["stage"])
                problems.append(f"   • {stage_name}: {item['drop_off']}% yo'qotish")

    if problems:
        lines.extend(problems[:5])  # Top 5 problems
    else:
        lines.append("   Hozircha muammo aniqlanmadi")

    return "\n".join(lines)


async def get_user_journey(telegram_id: int) -> str:
    """Get a specific user's journey through the bot."""
    user_events = [e for e in _events if e["telegram_id"] == telegram_id]

    if not user_events:
        return f"User {telegram_id} uchun ma'lumot yo'q."

    user_events.sort(key=lambda x: x["timestamp"])

    lines = [
        f"👤 <b>User Journey: {telegram_id}</b>",
        f"📊 Jami eventlar: {len(user_events)}",
        "",
    ]

    for e in user_events[-20:]:  # Last 20 events
        time_str = e["timestamp"].strftime("%H:%M:%S")
        lines.append(f"   {time_str} - {e['event_type']}")

    return "\n".join(lines)


async def get_feedback_analytics(days: int = 30) -> str:
    """Get feedback analytics from database."""
    from bot.database.models import Order, Complaint, User

    async with async_session_factory() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total completed orders
        result = await session.execute(
            select(func.count(Order.id)).where(
                Order.status == "completed",
                Order.created_at >= cutoff
            )
        )
        total_completed = result.scalar() or 0

        # Orders with good feedback
        result = await session.execute(
            select(func.count(Order.id)).where(
                Order.feedback == "good",
                Order.created_at >= cutoff
            )
        )
        good_feedback = result.scalar() or 0

        # Orders with bad feedback
        result = await session.execute(
            select(func.count(Order.id)).where(
                Order.feedback == "bad",
                Order.created_at >= cutoff
            )
        )
        bad_feedback = result.scalar() or 0

        # Orders without feedback (completed but no response)
        result = await session.execute(
            select(func.count(Order.id)).where(
                Order.status == "completed",
                Order.feedback == None,
                Order.created_at >= cutoff
            )
        )
        no_feedback = result.scalar() or 0

        # Total complaints
        result = await session.execute(
            select(func.count(Complaint.id)).where(
                Complaint.created_at >= cutoff
            )
        )
        total_complaints = result.scalar() or 0

        # Resolved complaints
        result = await session.execute(
            select(func.count(Complaint.id)).where(
                Complaint.status == "resolved",
                Complaint.created_at >= cutoff
            )
        )
        resolved_complaints = result.scalar() or 0

        # Worker statistics
        result = await session.execute(
            select(
                Order.assigned_username,
                func.count(Order.id).label("total"),
                func.sum(func.cast(Order.feedback == "good", Integer)).label("good"),
                func.sum(func.cast(Order.feedback == "bad", Integer)).label("bad"),
            ).where(
                Order.assigned_username != None,
                Order.status == "completed",
                Order.created_at >= cutoff
            ).group_by(Order.assigned_username)
        )
        worker_stats = result.fetchall()

        # Calculate percentages
        total_with_feedback = good_feedback + bad_feedback
        good_percent = round((good_feedback / total_with_feedback * 100), 1) if total_with_feedback > 0 else 0
        bad_percent = round((bad_feedback / total_with_feedback * 100), 1) if total_with_feedback > 0 else 0

        # Build report
        lines = [
            "📊 <b>FEEDBACK ANALITIKASI</b>",
            f"📅 So'nggi {days} kun",
            "",
            "📈 <b>Umumiy statistika:</b>",
            f"   • Yakunlangan buyurtmalar: {total_completed}",
            f"   • 👍 Yaxshi: {good_feedback} ({good_percent}%)",
            f"   • 👎 Yomon: {bad_feedback} ({bad_percent}%)",
            f"   • ❓ Javobsiz: {no_feedback}",
            "",
            "🚨 <b>Shikoyatlar:</b>",
            f"   • Jami: {total_complaints}",
            f"   • Hal qilingan: {resolved_complaints}",
            f"   • Kutilmoqda: {total_complaints - resolved_complaints}",
            "",
        ]

        # Worker breakdown
        if worker_stats:
            lines.append("👷 <b>Ishchilar bo'yicha:</b>")
            for row in worker_stats:
                username = row.assigned_username or "Noma'lum"
                total = row.total or 0
                good = row.good or 0
                bad = row.bad or 0
                good_pct = round((good / total * 100), 1) if total > 0 else 0

                # Rating emoji
                if good_pct >= 90:
                    rating = "⭐⭐⭐"
                elif good_pct >= 70:
                    rating = "⭐⭐"
                elif good_pct >= 50:
                    rating = "⭐"
                else:
                    rating = "⚠️"

                lines.append(f"   @{username}: {total} ta | 👍{good} 👎{bad} | {good_pct}% {rating}")

        # Satisfaction summary
        lines.append("")
        if good_percent >= 80:
            lines.append("✅ <b>Mijozlar juda mamnun!</b>")
        elif good_percent >= 60:
            lines.append("👍 <b>Mijozlar ko'pincha mamnun</b>")
        elif good_percent >= 40:
            lines.append("⚠️ <b>O'rtacha natija - yaxshilash kerak</b>")
        else:
            lines.append("🚨 <b>Diqqat! Ko'pchilik mijozlar noroziVaziyr</b>")

        return "\n".join(lines)

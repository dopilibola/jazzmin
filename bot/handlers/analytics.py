"""
Analytics handler - Admin only.
Shows bot statistics, funnel analysis, and user drop-off points.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.database.analytics import (
    generate_analytics_report,
    get_user_journey,
    get_events_since,
    get_unique_users,
    get_feedback_analytics,
)
from bot.keyboards.inline import analytics_inline
from bot.utils.texts import get_text
from bot_config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router(name="analytics")


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMIN_IDS


@router.message(Command("analiz"))
async def cmd_analytics(message: Message) -> None:
    """Handle /analiz command - admin only."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return

    await message.answer(
        "📊 <b>Analitika</b>\n\nDavr tanlang:",
        reply_markup=analytics_inline(),
    )


@router.message(F.text == "📊 Analiz")
async def btn_analytics(message: Message) -> None:
    """Handle Analiz button - admin only."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu tugma faqat adminlar uchun.")
        return

    await message.answer(
        "📊 <b>Analitika</b>\n\nDavr tanlang:",
        reply_markup=analytics_inline(),
    )


@router.callback_query(F.data.startswith("analytics:"))
async def analytics_callback(callback: CallbackQuery) -> None:
    """Handle analytics period selection."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    action = callback.data.split(":")[1]

    if action == "24h":
        report = await generate_analytics_report(hours=24)
    elif action == "7d":
        report = await generate_analytics_report(hours=168)
    elif action == "30d":
        report = await generate_analytics_report(hours=720)
    elif action == "summary":
        # Quick summary
        events = get_events_since(24)
        users = get_unique_users(events)
        report = (
            f"📊 <b>Tezkor statistika</b>\n\n"
            f"So'nggi 24 soat:\n"
            f"• Eventlar: {len(events)}\n"
            f"• Foydalanuvchilar: {len(users)}\n"
        )
    elif action == "feedback":
        report = await get_feedback_analytics(days=30)
    elif action == "feedback7":
        report = await get_feedback_analytics(days=7)
    else:
        report = "Noma'lum amal"

    # Split if too long
    if len(report) > 4000:
        parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for part in parts:
            await callback.message.answer(part)
    else:
        await callback.message.edit_text(
            report,
            reply_markup=analytics_inline(),
        )


@router.message(Command("userjourney"))
async def cmd_user_journey(message: Message) -> None:
    """Handle /userjourney <telegram_id> - admin only."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanish: /userjourney <telegram_id>")
        return

    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("Telegram ID raqam bo'lishi kerak.")
        return

    report = await get_user_journey(telegram_id)
    await message.answer(report)

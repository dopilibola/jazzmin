"""
Payment verification bot handler (BOT_TOKEN3).
Handles True/False callbacks for payment receipts.
"""
import asyncio
import logging
import socket

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from bot.database.db import async_session_factory
from bot.database.queries import get_order_by_id, update_order_status, get_grave_by_id
from bot.database.models import ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED
from bot.utils.texts import get_text
from bot_config import PAYMENT_BOT_TOKEN, BOT_TOKEN

logger = logging.getLogger(__name__)

verification_router = Router(name="payment_verification")


@verification_router.callback_query(lambda c: c.data and c.data.startswith("verify:"))
async def verify_payment_callback(callback: CallbackQuery) -> None:
    """Handle True/False verification from BOT_TOKEN3."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 5:
        return

    action = parts[1]  # "true" or "false"
    order_id = int(parts[2])
    user_telegram_id = int(parts[3])
    grave_id = int(parts[4]) if parts[4] != "0" else None

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.message.edit_caption(
                caption=callback.message.caption + "\n\n⚠️ Buyurtma topilmadi",
                reply_markup=None,
            )
            return

        # Get user language and user_id
        user_lang = order.user.language if order.user else "uz"
        user_id = order.user.id if order.user else None

        # Get grave info
        cemetery = "—"
        deceased = "—"
        if grave_id and user_id:
            grave = await get_grave_by_id(session, grave_id, user_id)
            if grave:
                cemetery = grave.cemetery or "—"
                deceased = grave.deceased_full_name or "—"

        if action == "true":
            # Update order status to paid
            await update_order_status(session, order_id, ORDER_STATUS_PAID)
            await session.commit()

            # Notify user via main bot
            try:
                main_session = AiohttpSession()
                main_session._connector_init["family"] = socket.AF_INET
                main_bot = Bot(
                    token=BOT_TOKEN,
                    session=main_session,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )
                await main_bot.send_message(
                    chat_id=user_telegram_id,
                    text=get_text(user_lang, "payment_verified", cemetery=cemetery, deceased=deceased),
                )
                await main_bot.session.close()
            except Exception as e:
                logger.error(f"Failed to notify user {user_telegram_id}: {e}")

            # Update caption
            await callback.message.edit_caption(
                caption=callback.message.caption + "\n\n✅ TASDIQLANDI",
                reply_markup=None,
            )

        else:  # action == "false"
            # Update order status to cancelled
            await update_order_status(session, order_id, ORDER_STATUS_CANCELLED)
            await session.commit()

            # Notify user via main bot
            try:
                main_session = AiohttpSession()
                main_session._connector_init["family"] = socket.AF_INET
                main_bot = Bot(
                    token=BOT_TOKEN,
                    session=main_session,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )
                await main_bot.send_message(
                    chat_id=user_telegram_id,
                    text=get_text(user_lang, "payment_not_verified", cemetery=cemetery, deceased=deceased),
                )
                await main_bot.session.close()
            except Exception as e:
                logger.error(f"Failed to notify user {user_telegram_id}: {e}")

            # Update caption
            await callback.message.edit_caption(
                caption=callback.message.caption + "\n\n❌ RAD ETILDI",
                reply_markup=None,
            )


async def run_verification_bot():
    """Run the verification bot (BOT_TOKEN3) separately."""
    if not PAYMENT_BOT_TOKEN:
        logger.warning("PAYMENT_BOT_TOKEN (BOT_TOKEN3) not configured. Verification bot disabled.")
        return

    logger.info("Starting payment verification bot...")

    # Create session with same settings as main bot
    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    session.timeout = 300

    bot = Bot(
        token=PAYMENT_BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(verification_router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()



"""
Payment verification bot handler (BOT_TOKEN3).
Handles True/False callbacks for payment receipts and photo verification.
"""
import asyncio
import logging
import socket
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InputMediaPhoto

from bot.database.db import async_session_factory
from bot.database.queries import get_order_by_id, update_order_status, get_grave_by_id
from bot.database.models import ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED
from bot.utils.texts import get_text
from bot.keyboards.inline import order_retry_inline, feedback_inline
from bot_config import PAYMENT_BOT_TOKEN, BOT_TOKEN, TELEGRAM_GROUP

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

                # Send order to Telegram group for workers (ONLY services, not flowers)
                from bot.handlers.order_workflow import send_order_to_group

                # Check if order contains services (not just flowers)
                is_service = False
                if order.items:
                    for item in order.items:
                        if item.item_type == "service":
                            is_service = True
                            break

                grave = None
                if grave_id and user_id:
                    grave = await get_grave_by_id(session, grave_id, user_id)

                # Only send to group if it's a service order
                await send_order_to_group(main_bot, order, grave, is_service=is_service)

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


# -----------------------------------------------------------------------------
# Photo verification callbacks (True/False for worker photos)
# -----------------------------------------------------------------------------


@verification_router.callback_query(lambda c: c.data and c.data.startswith("photo:"))
async def photo_verification_callback(callback: CallbackQuery) -> None:
    """Handle photo verification True/False from BOT_TOKEN3."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 5:
        return

    action = parts[1]  # "true" or "false"
    order_id = int(parts[2])
    user_telegram_id = int(parts[3])
    worker_telegram_id = int(parts[4])

    # Import here to avoid circular import
    from bot.handlers.order_workflow import _photo_uploads

    data = _photo_uploads.get(order_id, {})
    cemetery = data.get("cemetery", "—")
    deceased = data.get("deceased", "—")
    worker_username = data.get("worker_username", "—")

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.message.edit_text("Buyurtma topilmadi")
            return

        if action == "true":
            # Approved - send photos to customer
            order.status = "completed"
            await session.commit()

            # Send photos to customer via main bot
            if user_telegram_id and order.photo1_file_id and order.photo2_file_id:
                try:
                    main_session = AiohttpSession()
                    main_session._connector_init["family"] = socket.AF_INET
                    main_bot = Bot(
                        token=BOT_TOKEN,
                        session=main_session,
                        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                    )

                    user_lang = order.user.language if order.user else "uz"

                    # Send photos
                    media = [
                        InputMediaPhoto(
                            media=order.photo1_file_id,
                            caption=f"✅ Buyurtma #{order_id} bajarildi!\n\n"
                                    f"🏛 {cemetery}\n🪦 {deceased}"
                        ),
                        InputMediaPhoto(media=order.photo2_file_id),
                    ]
                    await main_bot.send_media_group(chat_id=user_telegram_id, media=media)

                    # Ask for feedback
                    await main_bot.send_message(
                        chat_id=user_telegram_id,
                        text=get_text(user_lang, "feedback_request"),
                        reply_markup=feedback_inline(order_id, user_lang),
                    )

                    # Notify worker in group
                    if TELEGRAM_GROUP:
                        await main_bot.send_message(
                            chat_id=int(TELEGRAM_GROUP),
                            text=f"@{worker_username} ✅ Buyurtma #{order_id} tasdiqlandi! Rahmat!"
                        )

                    await main_bot.session.close()
                except Exception as e:
                    logger.error(f"Failed to send photos to customer: {e}")

            # Update admin message
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ TASDIQLANDI - Mijozga yuborildi"
            )

            # Clean up
            _photo_uploads.pop(order_id, None)

        else:  # action == "false"
            # Rejected - send back to worker with options
            order.status = "rejected"
            order.retry_deadline = datetime.utcnow() + timedelta(hours=2)
            order.retry_reminder_sent = False
            await session.commit()

            # Update admin message
            await callback.message.edit_text(
                callback.message.text + "\n\n❌ RAD ETILDI - Ishchiga qaytarildi"
            )

            # Notify worker in group with buttons
            if TELEGRAM_GROUP:
                try:
                    main_session = AiohttpSession()
                    main_session._connector_init["family"] = socket.AF_INET
                    main_bot = Bot(
                        token=BOT_TOKEN,
                        session=main_session,
                        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                    )
                    await main_bot.send_message(
                        chat_id=int(TELEGRAM_GROUP),
                        text=f"@{worker_username} ❌ Buyurtma #{order_id} rad etildi!\n\n"
                             f"🏛 {cemetery} - {deceased}\n\n"
                             f"⏰ 2 soat ichida qaror qabul qiling:",
                        reply_markup=order_retry_inline(order_id, worker_telegram_id)
                    )
                    await main_bot.session.close()
                except Exception as e:
                    logger.error(f"Failed to notify worker: {e}")


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



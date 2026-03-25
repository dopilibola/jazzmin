"""
Order workflow: assignment, photo uploads, reminders, feedback.
Handles the flow after payment is confirmed.

FLOW:
1. Services → TELEGRAM_GROUP with "Buyurtma olindi" button
2. Flowers → Only to bot (no group)
3. Worker takes order → @mention notification with cemetery + deceased
4. 3 hour deadline, 2 hour reminder
5. Worker uploads 2 photos to GROUP → sent to BOT_TOKEN3 for verification
6. Admin True → photos to customer + feedback request
7. Admin False → back to worker (cancel/continue buttons, 2h deadline, 1h reminder)
8. Customer feedback → sent to worker in group
"""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message, PhotoSize, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database.db import async_session_factory
from bot.database.queries import (
    get_order_by_id,
    assign_order,
    upload_order_photo,
    get_orders_needing_reminder,
    mark_reminder_sent,
    get_overdue_orders,
)
from bot.services.finance import (
    assign_worker_to_order as assign_worker_financial,
    complete_order_financial,
    return_order_financial,
)
from bot.keyboards.inline import (
    order_take_inline,
    photo_verify_inline,
    order_retry_inline,
    feedback_inline,
    worker_retake_inline,
)
from bot.states.forms import FeedbackReasonState
from bot.utils.texts import get_text
from bot.utils.helpers import format_price
from bot_config import TELEGRAM_GROUP, PAYMENT_BOT_TOKEN, BOT_TOKEN, ADMIN_IDS

logger = logging.getLogger(__name__)

router = Router(name="order_workflow")

# Store for tracking photo uploads per order in group
# {order_id: {"worker_id": int, "photos": [file_id, ...], "message_ids": [int, ...]}}
_photo_uploads = {}


class PhotoUploadState(StatesGroup):
    """State for photo upload in group."""
    waiting_photo = State()


class RetryState(StatesGroup):
    """State for retry after rejection."""
    waiting_decision = State()
    waiting_photo = State()


# -----------------------------------------------------------------------------
# Send order to group (ONLY SERVICES, not flowers)
# -----------------------------------------------------------------------------


async def send_order_to_group(bot: Bot, order, grave=None, is_service: bool = True, items_list: list = None) -> None:
    """Send order notification to Telegram group after payment confirmed.

    ONLY for services. Flowers are handled directly in bot without group.
    User info and payment method are NOT shown for privacy.

    Args:
        items_list: Pre-loaded list of item titles (to avoid expired session issues)
    """
    if not is_service:
        # Flowers don't go to group
        logger.info(f"Order #{order.id} is flower order, skipping group notification")
        return

    if not TELEGRAM_GROUP:
        logger.warning("TELEGRAM_GROUP not configured")
        return

    try:
        group_id = int(TELEGRAM_GROUP)

        # Get grave info
        cemetery = "—"
        deceased = "—"
        birth_year = "—"
        death_year = "—"
        district = "—"

        if grave:
            cemetery = grave.cemetery or "—"
            deceased = grave.deceased_full_name or "—"
            birth_year = grave.birth_year or "—"
            death_year = grave.death_year or "—"
            district = grave.district or "—"
        elif order.cemetery:
            cemetery = order.cemetery.name if order.cemetery else "—"

        if order.district:
            district = order.district.name_uz if hasattr(order.district, 'name_uz') else str(order.district)

        if order.deceased_full_name:
            deceased = order.deceased_full_name
        if order.birth_year:
            birth_year = order.birth_year
        if order.death_year:
            death_year = order.death_year

        # Get services - use pre-loaded items_list if provided
        services_text = ""
        if items_list:
            services_text = "\n".join([f"   • {title}" for title in items_list])
        elif order.items:
            try:
                services_text = "\n".join([f"   • {item.title}" for item in order.items])
            except Exception:
                services_text = "   —"
        else:
            services_text = "   —"

        caption = (
            f"📋 YANGI BUYURTMA #{order.id}\n\n"
            f"📍 Tuman: {district}\n"
            f"🏛 Qabriston: {cemetery}\n"
            f"🪦 Marhum: {deceased}\n"
            f"📅 Tug'ilgan: {birth_year} | Vafot: {death_year}\n\n"
            f"🛒 Xizmat:\n{services_text}\n\n"
            f"💰 Jami: {format_price(order.total_price, 'uz')}"
        )

        await bot.send_message(
            chat_id=group_id,
            text=caption,
            reply_markup=order_take_inline(order.id),
        )
        logger.info(f"Order #{order.id} sent to group {group_id}")
    except Exception as e:
        logger.error(f"Failed to send order to group: {e}")


# -----------------------------------------------------------------------------
# Worker takes order (callback in group)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("order:take:"))
async def take_order_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Worker takes an order in the group."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    order_id = int(parts[2])
    worker_id = callback.from_user.id
    worker_username = callback.from_user.username or callback.from_user.first_name or "Ishchi"

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            await callback.answer("Buyurtma topilmadi", show_alert=True)
            return

        if order.assigned_telegram_id:
            await callback.answer(
                f"Bu buyurtma allaqachon @{order.assigned_username or 'boshqa kishi'} tomonidan olingan",
                show_alert=True
            )
            return

        # Assign order to worker
        await assign_order(session, order_id, worker_id, worker_username)
        await session.commit()

        # Assign worker to financial record
        try:
            await assign_worker_financial(session, order_id, worker_id, worker_username)
            await session.commit()
        except Exception as e:
            logger.debug(f"Financial worker assignment for order #{order_id}: {e}")

        # Get grave info for notification
        cemetery = "—"
        deceased = "—"

        if order.grave:
            cemetery = order.grave.cemetery or "—"
            deceased = order.grave.deceased_full_name or "—"
        else:
            if order.cemetery:
                cemetery = order.cemetery.name
            deceased = order.deceased_full_name or "—"

        # Update message in group - remove button
        try:
            new_text = callback.message.text + f"\n\n✅ BUYURTMA OLINDI: @{worker_username}"
            await callback.message.edit_text(new_text, reply_markup=None)
        except Exception:
            pass

        # Notify worker with @mention in group
        await callback.message.answer(
            f"@{worker_username} ✅ Siz <b>{cemetery}</b> qabristonidagi "
            f"<b>{deceased}</b> buyurtmasini oldingiz!\n\n"
            f"📋 Buyurtma #{order_id}\n"
            f"⏰ 3 soat ichida 2 ta rasm yuboring.\n\n"
            f"📸 Rasmlarni shu guruhga yuboring va qaysi buyurtma ekanini yozing.",
            parse_mode="HTML"
        )

        # Initialize photo tracking
        _photo_uploads[order_id] = {
            "worker_id": worker_id,
            "worker_username": worker_username,
            "photos": [],
            "cemetery": cemetery,
            "deceased": deceased,
        }

        # Notify customer that order is being worked on
        if order.user:
            user_lang = order.user.language or "uz"
            try:
                await _send_to_main_bot(
                    order.user.telegram_id,
                    get_text(user_lang, "order_taken_notify")
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")


# -----------------------------------------------------------------------------
# Receive photos in GROUP (not private chat)
# -----------------------------------------------------------------------------


@router.message(F.photo, F.chat.type.in_({"group", "supergroup"}))
async def receive_photo_in_group(message: Message) -> None:
    """Receive photo from worker in group. Must reply or mention order."""
    worker_id = message.from_user.id
    worker_username = message.from_user.username or message.from_user.first_name or "Ishchi"

    # Find which order this worker is assigned to
    order_id = None
    for oid, data in _photo_uploads.items():
        if data["worker_id"] == worker_id and len(data["photos"]) < 2:
            order_id = oid
            break

    if not order_id:
        # No active order for this worker
        return

    photo: PhotoSize = message.photo[-1]
    file_id = photo.file_id

    # Add photo to tracking
    _photo_uploads[order_id]["photos"].append(file_id)
    photo_count = len(_photo_uploads[order_id]["photos"])

    async with async_session_factory() as session:
        order, _ = await upload_order_photo(session, order_id, file_id)
        await session.commit()

    if photo_count == 1:
        await message.reply(
            f"@{worker_username} ✅ 1-rasm qabul qilindi!\n"
            f"📸 Yana 1 ta rasm yuboring."
        )
    elif photo_count == 2:
        # Both photos received - send to BOT_TOKEN3 for verification
        await message.reply(
            f"@{worker_username} ✅ 2-rasm qabul qilindi!\n"
            f"⏳ Rasmlar tekshiruvga yuborildi..."
        )

        # Send to BOT_TOKEN3 for admin verification
        await _send_photos_for_verification(order_id, message.bot)


async def _send_photos_for_verification(order_id: int, group_bot: Bot) -> None:
    """Send photos to BOT_TOKEN3 for admin verification."""
    if not PAYMENT_BOT_TOKEN:
        logger.warning("PAYMENT_BOT_TOKEN not configured")
        return

    data = _photo_uploads.get(order_id, {})
    photos = data.get("photos", [])
    cemetery = data.get("cemetery", "—")
    deceased = data.get("deceased", "—")
    worker_username = data.get("worker_username", "—")

    if len(photos) < 2:
        return

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            return

        user_telegram_id = order.user.telegram_id if order.user else 0

    try:
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.types import BufferedInputFile
        import socket

        verify_session = AiohttpSession()
        verify_session._connector_init["family"] = socket.AF_INET
        verify_bot = Bot(
            token=PAYMENT_BOT_TOKEN,
            session=verify_session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        # Download photos from group bot
        photo_bytes = []
        for file_id in photos:
            file = await group_bot.get_file(file_id)
            content = await group_bot.download_file(file.file_path)
            photo_bytes.append(content.read())
            content.seek(0)

        caption = (
            f"📸 RASMLAR TEKSHIRUVI\n\n"
            f"📋 Buyurtma #{order_id}\n"
            f"👷 Ishchi: @{worker_username}\n"
            f"🏛 Qabriston: {cemetery}\n"
            f"🪦 Marhum: {deceased}\n\n"
            f"✅ True - Mijozga yuborish\n"
            f"❌ False - Rad etish"
        )

        # Send to admins
        for admin_id in ADMIN_IDS:
            try:
                media = [
                    InputMediaPhoto(
                        media=BufferedInputFile(photo_bytes[0], filename="photo1.jpg"),
                        caption=caption
                    ),
                    InputMediaPhoto(
                        media=BufferedInputFile(photo_bytes[1], filename="photo2.jpg")
                    ),
                ]
                await verify_bot.send_media_group(chat_id=admin_id, media=media)
                await verify_bot.send_message(
                    chat_id=admin_id,
                    text="Rasmlarni tasdiqlaysizmi?",
                    reply_markup=photo_verify_inline(order_id, user_telegram_id, data.get("worker_id", 0)),
                )
            except Exception as e:
                logger.error(f"Failed to send to admin {admin_id}: {e}")

        await verify_bot.session.close()

    except Exception as e:
        logger.error(f"Failed to send photos for verification: {e}")


# NOTE: Photo verification callbacks (photo:true/false) are handled in payment_verification.py
# since they are processed by BOT_TOKEN3


async def _send_photos_to_customer(
    user_telegram_id: int,
    photo1_file_id: str,
    photo2_file_id: str,
    cemetery: str,
    deceased: str,
    order_id: int,
    lang: str
) -> None:
    """Send approved photos to customer and ask for feedback."""
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    import socket

    main_session = AiohttpSession()
    main_session._connector_init["family"] = socket.AF_INET
    main_bot = Bot(
        token=BOT_TOKEN,
        session=main_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        # Send photos
        media = [
            InputMediaPhoto(
                media=photo1_file_id,
                caption=f"✅ Buyurtma #{order_id} bajarildi!\n\n"
                        f"🏛 {cemetery}\n🪦 {deceased}"
            ),
            InputMediaPhoto(media=photo2_file_id),
        ]
        await main_bot.send_media_group(chat_id=user_telegram_id, media=media)

        # Ask for feedback
        await main_bot.send_message(
            chat_id=user_telegram_id,
            text=get_text(lang, "feedback_request"),
            reply_markup=feedback_inline(order_id, lang),
        )
    finally:
        await main_bot.session.close()


# -----------------------------------------------------------------------------
# Retry callbacks (worker decides to cancel or continue)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("retry:"))
async def retry_order_callback(callback: CallbackQuery) -> None:
    """Handle worker's decision after rejection."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 4:
        return

    action = parts[1]  # "cancel" or "continue"
    order_id = int(parts[2])
    worker_id = int(parts[3])

    # Verify this is the assigned worker
    if callback.from_user.id != worker_id:
        await callback.answer("Bu buyurtma sizga biriktirilmagan!", show_alert=True)
        return

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.answer("Buyurtma topilmadi", show_alert=True)
            return

        worker_username = callback.from_user.username or callback.from_user.first_name or "Ishchi"

        if action == "cancel":
            # Worker gives up - reset order for reassignment
            order.assigned_telegram_id = None
            order.assigned_username = None
            order.assigned_at = None
            order.photo1_file_id = None
            order.photo2_file_id = None
            order.status = "paid"  # Back to paid, ready for new worker
            await session.commit()

            # Clean up
            _photo_uploads.pop(order_id, None)

            await callback.message.edit_text(
                callback.message.text + f"\n\n🚫 @{worker_username} buyurtmadan voz kechdi."
            )

            # Re-send order to group for new worker
            cemetery = order.grave.cemetery if order.grave else (order.cemetery.name if order.cemetery else "—")
            deceased = order.grave.deceased_full_name if order.grave else (order.deceased_full_name or "—")

            await callback.message.answer(
                f"📋 BUYURTMA QAYTA OCHIQ #{order_id}\n\n"
                f"🏛 {cemetery}\n"
                f"🪦 {deceased}\n\n"
                f"Kim oladi?",
                reply_markup=order_take_inline(order_id)
            )

        else:  # action == "continue"
            # Worker will try again
            order.status = "in_progress"
            order.photo1_file_id = None
            order.photo2_file_id = None
            order.assigned_at = datetime.utcnow()  # Reset deadline
            await session.commit()

            # Reset photo tracking
            _photo_uploads[order_id] = {
                "worker_id": worker_id,
                "worker_username": worker_username,
                "photos": [],
                "cemetery": order.grave.cemetery if order.grave else "—",
                "deceased": order.grave.deceased_full_name if order.grave else "—",
            }

            await callback.message.edit_text(
                callback.message.text + f"\n\n🔄 @{worker_username} davom etmoqda."
            )

            await callback.message.answer(
                f"@{worker_username} ✅ Buyurtma #{order_id} sizda qoldi.\n\n"
                f"⏰ 3 soat ichida yangi 2 ta rasm yuboring."
            )


# -----------------------------------------------------------------------------
# Customer feedback callbacks
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("feedback:"))
async def feedback_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle customer feedback."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    rating = parts[1]  # "good" or "bad"
    order_id = int(parts[2])

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            return

        worker_username = order.assigned_username or "Ishchi"
        cemetery = order.grave.cemetery if order.grave else (order.cemetery.name if order.cemetery else "—")
        deceased = order.grave.deceased_full_name if order.grave else (order.deceased_full_name or "—")
        user_lang = order.user.language if order.user else "uz"

        if rating == "good":
            # Save feedback
            order.feedback = rating
            await session.commit()

            # Update customer message
            await callback.message.edit_text(
                callback.message.text + f"\n\n👍 Fikringiz uchun rahmat!"
            )

            # Send feedback to worker in group
            if TELEGRAM_GROUP:
                try:
                    await _send_to_group(
                        f"📊 FEEDBACK - Buyurtma #{order_id}\n\n"
                        f"👷 @{worker_username}\n"
                        f"🏛 {cemetery} - {deceased}\n\n"
                        f"👍 Yaxshi bajarilgan! ✅"
                    )
                except Exception as e:
                    logger.error(f"Failed to send feedback to group: {e}")
        else:
            # Bad feedback - ask for reason
            await state.set_state(FeedbackReasonState.waiting_reason)
            await state.update_data(
                order_id=order_id,
                worker_username=worker_username,
                cemetery=cemetery,
                deceased=deceased,
                user_lang=user_lang,
            )

            await callback.message.edit_text(
                callback.message.text + "\n\n👎 Yomon"
            )

            # Ask for reason
            reason_prompt = get_text(user_lang, "feedback_reason_prompt")
            await callback.message.answer(reason_prompt)


# -----------------------------------------------------------------------------
# Feedback reason handler (when user writes why they didn't like the service)
# -----------------------------------------------------------------------------


@router.message(FeedbackReasonState.waiting_reason, F.text)
async def receive_feedback_reason(message: Message, state: FSMContext) -> None:
    """Receive feedback reason from customer who clicked 'bad'.

    Simple flow:
    1. Send to admin (BOT_TOKEN3) with photos + reason
    2. Send to Telegram group
    3. Auto-send to worker with retake/cancel buttons
    """
    reason_text = (message.text or "").strip()
    if len(reason_text) < 5:
        await message.answer("Iltimos, sababni batafsilroq yozing (kamida 5 ta belgi).")
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    worker_username = data.get("worker_username", "Ishchi")
    cemetery = data.get("cemetery", "—")
    deceased = data.get("deceased", "—")
    user_lang = data.get("user_lang", "uz")

    if not order_id:
        await state.clear()
        return

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await state.clear()
            return

        worker_telegram_id = order.assigned_telegram_id or 0
        photo1 = order.photo1_file_id
        photo2 = order.photo2_file_id

        # Save feedback with reason
        order.feedback = "bad"
        order.feedback_reason = reason_text
        await session.commit()

    await state.clear()

    # Notify customer
    await message.answer(get_text(user_lang, "feedback_reason_received"))

    # Send to admin via BOT_TOKEN3 with photos and action buttons
    if PAYMENT_BOT_TOKEN:
        try:
            await _send_bad_feedback_to_admin(
                order_id=order_id,
                worker_telegram_id=worker_telegram_id,
                worker_username=worker_username,
                cemetery=cemetery,
                deceased=deceased,
                reason_text=reason_text,
                photo1_file_id=photo1,
                photo2_file_id=photo2,
            )
        except Exception as e:
            logger.error(f"Failed to send bad feedback to admin: {e}")


async def _send_bad_feedback_to_admin(
    order_id: int,
    worker_telegram_id: int,
    worker_username: str,
    cemetery: str,
    deceased: str,
    reason_text: str,
    photo1_file_id: str | None,
    photo2_file_id: str | None,
) -> None:
    """Send bad feedback with photos to admin via BOT_TOKEN3 with action buttons."""
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
    import socket

    # First, download photos from main bot (file_ids are bot-specific)
    photo_bytes = []
    if photo1_file_id or photo2_file_id:
        main_session = AiohttpSession()
        main_session._connector_init["family"] = socket.AF_INET
        main_bot = Bot(
            token=BOT_TOKEN,
            session=main_session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            for file_id in [photo1_file_id, photo2_file_id]:
                if file_id:
                    try:
                        file = await main_bot.get_file(file_id)
                        content = await main_bot.download_file(file.file_path)
                        photo_bytes.append(content.read())
                    except Exception as e:
                        logger.error(f"Failed to download photo: {e}")
        finally:
            await main_bot.session.close()

    verify_session = AiohttpSession()
    verify_session._connector_init["family"] = socket.AF_INET
    verify_bot = Bot(
        token=PAYMENT_BOT_TOKEN,
        session=verify_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        caption = (
            f"👎 SALBIY FEEDBACK - Buyurtma #{order_id}\n\n"
            f"👷 Ishchi: @{worker_username}\n"
            f"🏛 Qabriston: {cemetery}\n"
            f"🪦 Marhum: {deceased}\n\n"
            f"📝 <b>Mijoz sababi:</b>\n{reason_text}"
        )

        # Admin action buttons
        admin_buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Ishchiga yuborish",
                        callback_data=f"badfb:toworker:{order_id}:{worker_telegram_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Guruhga qayta yuborish",
                        callback_data=f"badfb:togroup:{order_id}",
                    ),
                ],
            ]
        )

        # Send to all admins
        for admin_id in ADMIN_IDS:
            try:
                # Send photos if available (re-upload as BufferedInputFile)
                if len(photo_bytes) >= 2:
                    media = [
                        InputMediaPhoto(
                            media=BufferedInputFile(photo_bytes[0], filename="photo1.jpg"),
                            caption=caption
                        ),
                        InputMediaPhoto(
                            media=BufferedInputFile(photo_bytes[1], filename="photo2.jpg")
                        ),
                    ]
                    await verify_bot.send_media_group(chat_id=admin_id, media=media)
                elif len(photo_bytes) == 1:
                    await verify_bot.send_photo(
                        chat_id=admin_id,
                        photo=BufferedInputFile(photo_bytes[0], filename="photo.jpg"),
                        caption=caption
                    )
                else:
                    await verify_bot.send_message(chat_id=admin_id, text=caption)

                # Send action buttons
                await verify_bot.send_message(
                    chat_id=admin_id,
                    text="Nima qilasiz?",
                    reply_markup=admin_buttons,
                )
            except Exception as e:
                logger.error(f"Failed to send to admin {admin_id}: {e}")
    finally:
        await verify_bot.session.close()


# -----------------------------------------------------------------------------
# Reclean callbacks (worker accepts/cancels reclean request from complaint)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("reclean:"))
async def reclean_callback(callback: CallbackQuery) -> None:
    """Handle worker's decision on reclean request from complaint."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    action = parts[1]  # "accept" or "cancel"
    order_id = int(parts[2])

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.message.edit_text("Buyurtma topilmadi")
            return

        worker_username = order.assigned_username or "Ishchi"
        worker_telegram_id = order.assigned_telegram_id or 0
        cemetery = order.grave.cemetery if order.grave else (order.cemetery.name if order.cemetery else "—")
        deceased = order.grave.deceased_full_name if order.grave else (order.deceased_full_name or "—")

        district = "—"
        if order.district:
            district = order.district.name_uz if hasattr(order.district, 'name_uz') else str(order.district)

        services_text = ""
        if order.items:
            services_text = "\n".join([f"   • {item.title}" for item in order.items])
        else:
            services_text = "   —"

        total_price = order.total_price

        if action == "accept":
            # Verify this is the assigned worker
            if len(parts) >= 4:
                expected_worker_id = int(parts[3])
                if callback.from_user.id != expected_worker_id:
                    await callback.answer("Bu buyurtma sizga tegishli emas!", show_alert=True)
                    return

            # Worker accepts re-cleaning
            order.status = "in_progress"
            order.photo1_file_id = None
            order.photo2_file_id = None
            order.photos_uploaded_at = None
            order.feedback = None
            order.feedback_reason = None
            order.assigned_at = datetime.utcnow()
            order.reminder_sent = False
            await session.commit()

            await callback.message.edit_text(
                callback.message.text + "\n\n✅ Siz qayta tozalashni qabul qildingiz. 3 soat ichida 2 ta rasm yuboring."
            )

            # Re-initialize photo tracking
            _photo_uploads[order_id] = {
                "worker_id": worker_telegram_id,
                "worker_username": worker_username,
                "photos": [],
                "cemetery": cemetery,
                "deceased": deceased,
            }

            # Notify in group
            if TELEGRAM_GROUP:
                try:
                    await _send_to_group(
                        f"@{worker_username} ✅ Buyurtma #{order_id}ni qayta tozalash uchun oldi.\n"
                        f"⏰ 3 soat ichida 2 ta rasm kutilmoqda."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify group: {e}")

        else:  # action == "cancel"
            # Worker declines - reset order for new worker
            order.assigned_telegram_id = None
            order.assigned_username = None
            order.assigned_at = None
            order.photo1_file_id = None
            order.photo2_file_id = None
            order.photos_uploaded_at = None
            order.status = "paid"
            order.feedback = None
            order.feedback_reason = None
            order.reminder_sent = False
            await session.commit()

            # Clean up photo tracking
            _photo_uploads.pop(order_id, None)

            await callback.message.edit_text(
                callback.message.text + "\n\n❌ Siz qayta tozalashdan voz kechdingiz. Buyurtma guruhga yuborildi."
            )

            # Post to group for new workers
            if TELEGRAM_GROUP:
                try:
                    await _send_to_group_with_buttons(
                        f"🔄 QAYTA BUYURTMA #{order_id}\n\n"
                        f"⚠️ Oldingi ishchi qayta tozalashdan voz kechdi!\n\n"
                        f"📍 Tuman: {district}\n"
                        f"🏛 Qabriston: {cemetery}\n"
                        f"🪦 Marhum: {deceased}\n\n"
                        f"🛒 Xizmat:\n{services_text}\n\n"
                        f"💰 Jami: {format_price(total_price, 'uz')}",
                        order_take_inline(order_id)
                    )
                except Exception as e:
                    logger.error(f"Failed to post order to group: {e}")


# -----------------------------------------------------------------------------
# Background reminder task
# -----------------------------------------------------------------------------


async def check_reminders(bot: Bot) -> None:
    """Background task to check for orders needing reminders."""
    while True:
        try:
            async with async_session_factory() as session:
                # Check 2-hour reminders (for 3-hour deadline)
                orders = await get_orders_needing_reminder(session, hours=2)
                for order in orders:
                    if order.assigned_telegram_id and TELEGRAM_GROUP:
                        try:
                            cemetery = order.grave.cemetery if order.grave else "—"
                            deceased = order.grave.deceased_full_name if order.grave else "—"

                            await bot.send_message(
                                chat_id=int(TELEGRAM_GROUP),
                                text=f"⚠️ ESLATMA: @{order.assigned_username}\n\n"
                                     f"📋 Buyurtma #{order.id}\n"
                                     f"🏛 {cemetery} - {deceased}\n\n"
                                     f"⏰ 1 soat qoldi! Iltimos, 2 ta rasm yuboring."
                            )
                            await mark_reminder_sent(session, order.id)
                            await session.commit()
                        except Exception as e:
                            logger.error(f"Failed to send reminder: {e}")

                # Check retry reminders (1 hour into 2-hour deadline)
                retry_orders = await get_retry_orders_needing_reminder(session)
                for order in retry_orders:
                    if order.assigned_telegram_id and TELEGRAM_GROUP:
                        try:
                            await bot.send_message(
                                chat_id=int(TELEGRAM_GROUP),
                                text=f"⚠️ ESLATMA: @{order.assigned_username}\n\n"
                                     f"📋 Buyurtma #{order.id}\n"
                                     f"⏰ 1 soat qoldi! Qaror qabul qiling."
                            )
                            order.retry_reminder_sent = True
                            await session.commit()
                        except Exception as e:
                            logger.error(f"Failed to send retry reminder: {e}")

                # Check overdue orders (3+ hours)
                overdue = await get_overdue_orders(session, hours=3)
                for order in overdue:
                    if order.assigned_telegram_id and TELEGRAM_GROUP:
                        try:
                            cemetery = order.grave.cemetery if order.grave else "—"
                            deceased = order.grave.deceased_full_name if order.grave else "—"

                            await bot.send_message(
                                chat_id=int(TELEGRAM_GROUP),
                                text=f"🚨 MUDDATI O'TDI: @{order.assigned_username}\n\n"
                                     f"📋 Buyurtma #{order.id}\n"
                                     f"🏛 {cemetery} - {deceased}\n\n"
                                     f"❌ Buyurtma boshqa ishchiga o'tkaziladi."
                            )

                            # Reset order for reassignment
                            order.assigned_telegram_id = None
                            order.assigned_username = None
                            order.assigned_at = None
                            order.status = "paid"
                            await session.commit()

                            # Clean up
                            _photo_uploads.pop(order.id, None)

                            # Re-post for new worker
                            await bot.send_message(
                                chat_id=int(TELEGRAM_GROUP),
                                text=f"📋 BUYURTMA QAYTA OCHIQ #{order.id}\n\n"
                                     f"🏛 {cemetery}\n"
                                     f"🪦 {deceased}",
                                reply_markup=order_take_inline(order.id)
                            )

                        except Exception as e:
                            logger.error(f"Failed to handle overdue order: {e}")

        except Exception as e:
            logger.error(f"Error in reminder check: {e}")

        # Check every 5 minutes
        await asyncio.sleep(300)


async def get_retry_orders_needing_reminder(session):
    """Get orders in retry state needing 1-hour reminder."""
    from sqlalchemy import select
    from bot.database.models import Order

    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    result = await session.execute(
        select(Order).where(
            Order.status == "rejected",
            Order.retry_reminder_sent == False,
            Order.retry_deadline != None,
            Order.assigned_at <= one_hour_ago,
        )
    )
    return result.scalars().all()


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


async def _send_to_main_bot(chat_id: int, text: str) -> None:
    """Send message via main bot."""
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    import socket

    main_session = AiohttpSession()
    main_session._connector_init["family"] = socket.AF_INET
    main_bot = Bot(
        token=BOT_TOKEN,
        session=main_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await main_bot.send_message(chat_id=chat_id, text=text)
    finally:
        await main_bot.session.close()


async def _send_to_group(text: str) -> None:
    """Send message to Telegram group via main bot."""
    if not TELEGRAM_GROUP:
        return
    await _send_to_main_bot(int(TELEGRAM_GROUP), text)


async def _send_to_group_with_buttons(text: str, markup) -> None:
    """Send message with buttons to Telegram group."""
    if not TELEGRAM_GROUP or not BOT_TOKEN:
        return

    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    import socket

    main_session = AiohttpSession()
    main_session._connector_init["family"] = socket.AF_INET
    main_bot = Bot(
        token=BOT_TOKEN,
        session=main_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await main_bot.send_message(
            chat_id=int(TELEGRAM_GROUP),
            text=text,
            reply_markup=markup
        )
    finally:
        await main_bot.session.close()


def start_reminder_task(bot: Bot) -> None:
    """Start the background reminder task."""
    asyncio.create_task(check_reminders(bot))

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
from aiogram.types import CallbackQuery, InputMediaPhoto, Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.db import async_session_factory
from bot.database.queries import get_order_by_id, update_order_status, get_grave_by_id
from bot.database.models import ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED
from bot.services.finance import (
    create_financial_for_order,
    complete_order_financial,
    cancel_order_financial,
    assign_worker_to_order as assign_worker_financial,
)
from bot.utils.texts import get_text
from bot.keyboards.inline import (
    order_retry_inline,
    feedback_inline,
    bad_feedback_admin_inline,
    worker_retake_inline,
    order_take_inline,
)
from bot_config import PAYMENT_BOT_TOKEN, BOT_TOKEN, TELEGRAM_GROUP, ADMIN_IDS, ADMIN_CHAT_ID
from bot.utils.helpers import format_price

logger = logging.getLogger(__name__)

verification_router = Router(name="payment_verification")


def _build_admin_payment_text(info: dict) -> str:
    """To'lov tasdiqlangach adminga yuboriladigan to'liq ma'lumot (HTML)."""
    birth = info.get("birth") or "—"
    death = info.get("death") or "—"
    services = info.get("services") or "—"
    lines = [
        "💰 <b>TO'LOV TASDIQLANDI</b>",
        f"🧾 Buyurtma: <b>#{info['order_id']}</b>",
        "",
        "👤 <b>Mijoz</b>",
        f"• Ism: {info.get('name') or '—'}",
        f"• Telefon: {info.get('phone') or '—'}",
        f"• Chat ID: <code>{info.get('chat_id') or '—'}</code>",
        f"• Til: {info.get('lang') or '—'}",
        "",
        "🪦 <b>Qabr</b>",
        f"• Marhum: {info.get('deceased') or '—'}",
        f"• Qarindoshlik: {info.get('relationship') or '—'}",
        f"• Viloyat / Tuman: {info.get('region') or '—'} / {info.get('district') or '—'}",
        f"• Qabriston: {info.get('cemetery') or '—'}",
        f"• Yillar: {birth} – {death}",
        "",
        "🧹 <b>Buyurtma</b>",
        f"• Xizmat(lar): {services}",
        f"• Jami: {info.get('total') or '—'}",
        f"• To'lov usuli: {info.get('payment') or '—'}",
        f"• Izoh: {info.get('comment') or '—'}",
        f"• Sana: {info.get('created') or '—'}",
    ]
    return "\n".join(lines)


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
            # Check if order contains services BEFORE commit (items expire after commit)
            is_service = False
            items_list = []  # Store item titles before commit
            if order.items:
                logger.info(f"Order #{order_id} has {len(order.items)} items")
                for item in order.items:
                    items_list.append(item.title)
                    logger.info(f"  Item: {item.title}, type: {item.item_type}")
                    if item.item_type == "service":
                        is_service = True
            else:
                logger.warning(f"Order #{order_id} has NO items!")

            logger.info(f"Order #{order_id}: is_service={is_service}, items_list={items_list}")

            # Get grave info before commit
            grave = None
            if grave_id and user_id:
                grave = await get_grave_by_id(session, grave_id, user_id)

            # --- Admin uchun to'liq ma'lumotni commit'dan OLDIN yig'amiz ---
            # (commit'dan keyin ORM atributlari muddati o'tib, qayta so'rov talab qiladi)
            admin_info = {
                "order_id": order_id,
                "name": order.full_name or (order.user.full_name if order.user else "") or "—",
                "phone": order.phone_number or (order.user.phone_number if order.user else "") or "—",
                "chat_id": user_telegram_id,
                "lang": user_lang,
                "deceased": (grave.deceased_full_name if grave else order.deceased_full_name) or deceased,
                "relationship": (grave.relationship_status if grave else "") or "—",
                "region": (grave.region if grave else "") or "—",
                "district": (grave.district if grave else "") or "—",
                "cemetery": (grave.cemetery if grave else "") or cemetery,
                "birth": (grave.birth_year if grave else order.birth_year),
                "death": (grave.death_year if grave else order.death_year),
                "services": ", ".join(items_list) if items_list else "—",
                "total": format_price(order.total_price or 0),
                "payment": order.payment_method or "—",
                "comment": order.comment or "—",
                "created": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "—",
            }

            # Update order status to paid
            await update_order_status(session, order_id, ORDER_STATUS_PAID)
            await session.commit()

            # Create financial record for the order
            try:
                await create_financial_for_order(order_id)
                logger.info(f"Created financial record for order #{order_id}")
            except Exception as e:
                logger.error(f"Failed to create financial record for order #{order_id}: {e}")

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

                # Only send to group if it's a service order
                await send_order_to_group(main_bot, order, grave, is_service=is_service, items_list=items_list)

                await main_bot.session.close()
            except Exception as e:
                logger.error(f"Failed to notify user {user_telegram_id}: {e}")

            # To'lov tasdiqlangach — adminga TO'LIQ ma'lumot (BOT_TOKEN3 orqali)
            if ADMIN_CHAT_ID:
                try:
                    await callback.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=_build_admin_payment_text(admin_info),
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {ADMIN_CHAT_ID} for order #{order_id}: {e}")
            else:
                logger.warning("TELEGRAM_ADMIN_CHAT_ID not set — admin payment notification skipped.")

            # Update caption
            await callback.message.edit_caption(
                caption=callback.message.caption + "\n\n✅ TASDIQLANDI",
                reply_markup=None,
            )

        else:  # action == "false"
            # Update order status to cancelled
            await update_order_status(session, order_id, ORDER_STATUS_CANCELLED)
            await session.commit()

            # Cancel financial record if exists
            try:
                await cancel_order_financial(session, order_id)
                await session.commit()
            except Exception as e:
                logger.debug(f"No financial to cancel for order #{order_id}: {e}")

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

            # Complete financial record and update worker earnings
            try:
                await complete_order_financial(session, order_id)
                await session.commit()
                logger.info(f"Completed financial record for order #{order_id}")
            except Exception as e:
                logger.error(f"Failed to complete financial for order #{order_id}: {e}")

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


# -----------------------------------------------------------------------------
# Bad feedback admin actions (Re-feedback or Redo order)
# -----------------------------------------------------------------------------


@verification_router.callback_query(lambda c: c.data and c.data.startswith("badfb:"))
async def bad_feedback_admin_callback(callback: CallbackQuery) -> None:
    """Handle admin actions on bad feedback: toworker or togroup."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    action = parts[1]  # "toworker" or "togroup"
    order_id = int(parts[2])

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.message.edit_text("Buyurtma topilmadi")
            return

        worker_telegram_id = order.assigned_telegram_id or 0
        worker_username = order.assigned_username or "Ishchi"
        cemetery = order.grave.cemetery if order.grave else (order.cemetery.name if order.cemetery else "—")
        deceased = order.grave.deceased_full_name if order.grave else (order.deceased_full_name or "—")
        reason_text = order.feedback_reason or ""

        district = "—"
        if order.district:
            district = order.district.name_uz if hasattr(order.district, 'name_uz') else str(order.district)

        services_text = ""
        if order.items:
            services_text = "\n".join([f"   • {item.title}" for item in order.items])
        else:
            services_text = "   —"

        total_price = order.total_price

        if action == "toworker":
            # Send to worker with retake/cancel buttons
            if len(parts) < 5:
                return
            worker_telegram_id = int(parts[4])

            try:
                main_session = AiohttpSession()
                main_session._connector_init["family"] = socket.AF_INET
                main_bot = Bot(
                    token=BOT_TOKEN,
                    session=main_session,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )

                # Send directly to worker
                await main_bot.send_message(
                    chat_id=worker_telegram_id,
                    text=f"⚠️ BUYURTMA QAYTARILDI - #{order_id}\n\n"
                         f"🏛 Qabriston: {cemetery}\n"
                         f"🪦 Marhum: {deceased}\n\n"
                         f"👎 Mijoz ishdan norozi. Qayta bajarasizmi?",
                    reply_markup=worker_retake_inline(order_id, worker_telegram_id),
                )

                # Also notify in group
                if TELEGRAM_GROUP:
                    await main_bot.send_message(
                        chat_id=int(TELEGRAM_GROUP),
                        text=f"⚠️ @{worker_username} - Buyurtma #{order_id} qaytarildi!\n"
                             f"Mijoz noroziligi sababli qayta bajarish kerak.",
                    )

                await main_bot.session.close()
            except Exception as e:
                logger.error(f"Failed to send redo request to worker: {e}")

            await callback.message.edit_text(
                callback.message.text + "\n\n✅ Ishchiga yuborildi"
            )

        elif action == "togroup":
            # Reset order and post to group directly
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

            try:
                main_session = AiohttpSession()
                main_session._connector_init["family"] = socket.AF_INET
                main_bot = Bot(
                    token=BOT_TOKEN,
                    session=main_session,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )

                if TELEGRAM_GROUP:
                    caption = (
                        f"🔄 QAYTA BUYURTMA #{order_id}\n\n"
                        f"⚠️ Mijoz oldingi ishdan norozi!\n\n"
                        f"📍 Tuman: {district}\n"
                        f"🏛 Qabriston: {cemetery}\n"
                        f"🪦 Marhum: {deceased}\n\n"
                        f"🛒 Xizmat:\n{services_text}\n\n"
                        f"💰 Jami: {format_price(total_price, 'uz')}"
                    )

                    await main_bot.send_message(
                        chat_id=int(TELEGRAM_GROUP),
                        text=caption,
                        reply_markup=order_take_inline(order_id),
                    )

                await main_bot.session.close()
            except Exception as e:
                logger.error(f"Failed to post order to group: {e}")

            await callback.message.edit_text(
                callback.message.text + "\n\n🔄 Guruhga qayta yuborildi"
            )


# -----------------------------------------------------------------------------
# Worker retake/cancel actions
# -----------------------------------------------------------------------------


@verification_router.callback_query(lambda c: c.data and c.data.startswith("retake:"))
async def worker_retake_callback(callback: CallbackQuery) -> None:
    """Handle worker decision to retake or cancel returned order."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 4:
        return

    action = parts[1]  # "accept" or "cancel"
    order_id = int(parts[2])
    worker_telegram_id = int(parts[3])

    # Verify this is the assigned worker
    if callback.from_user.id != worker_telegram_id:
        await callback.answer("Bu buyurtma sizga tegishli emas!", show_alert=True)
        return

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.message.edit_text("Buyurtma topilmadi")
            return

        worker_username = order.assigned_username or "Ishchi"
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
            # Worker accepts to redo
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
                callback.message.text + "\n\n✅ Siz buyurtmani qayta oldingiz. 3 soat ichida 2 ta rasm yuboring."
            )

            # Notify in group
            try:
                main_session = AiohttpSession()
                main_session._connector_init["family"] = socket.AF_INET
                main_bot = Bot(
                    token=BOT_TOKEN,
                    session=main_session,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )

                if TELEGRAM_GROUP:
                    await main_bot.send_message(
                        chat_id=int(TELEGRAM_GROUP),
                        text=f"@{worker_username} ✅ Buyurtma #{order_id}ni qayta oldi.\n"
                             f"⏰ 3 soat ichida 2 ta rasm kutilmoqda.",
                    )

                # Re-initialize photo tracking
                from bot.handlers.order_workflow import _photo_uploads
                _photo_uploads[order_id] = {
                    "worker_id": worker_telegram_id,
                    "worker_username": worker_username,
                    "photos": [],
                    "cemetery": cemetery,
                    "deceased": deceased,
                }

                await main_bot.session.close()
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

            await callback.message.edit_text(
                callback.message.text + "\n\n❌ Siz buyurtmadan voz kechdingiz. Guruhga qayta yuborildi."
            )

            # Post to group for new workers
            try:
                main_session = AiohttpSession()
                main_session._connector_init["family"] = socket.AF_INET
                main_bot = Bot(
                    token=BOT_TOKEN,
                    session=main_session,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )

                if TELEGRAM_GROUP:
                    caption = (
                        f"🔄 QAYTA BUYURTMA #{order_id}\n\n"
                        f"⚠️ Oldingi ishchi voz kechdi!\n\n"
                        f"📍 Tuman: {district}\n"
                        f"🏛 Qabriston: {cemetery}\n"
                        f"🪦 Marhum: {deceased}\n\n"
                        f"🛒 Xizmat:\n{services_text}\n\n"
                        f"💰 Jami: {format_price(total_price, 'uz')}"
                    )

                    await main_bot.send_message(
                        chat_id=int(TELEGRAM_GROUP),
                        text=caption,
                        reply_markup=order_take_inline(order_id),
                    )

                await main_bot.session.close()
            except Exception as e:
                logger.error(f"Failed to post order to group: {e}")


# -----------------------------------------------------------------------------
# Complaint admin callbacks
# -----------------------------------------------------------------------------

# State storage for admin response
_admin_response_state = {}  # {admin_id: {"complaint_id": int, "user_id": int}}


@verification_router.callback_query(lambda c: c.data and c.data.startswith("complaint:"))
async def complaint_admin_callback(callback: CallbackQuery) -> None:
    """Handle admin actions on complaint: respond or reclean."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    action = parts[1]  # "respond" or "reclean"

    if action == "respond":
        # Admin wants to respond to user
        if len(parts) < 4:
            return
        complaint_id = int(parts[2])
        user_id = int(parts[3])

        _admin_response_state[callback.from_user.id] = {
            "complaint_id": complaint_id,
            "user_id": user_id,
        }

        await callback.message.edit_text(
            callback.message.text + "\n\n📝 Mijozga yubormoqchi bo'lgan xabaringizni yozing:"
        )

    elif action == "reclean":
        # Admin wants to send for re-cleaning
        if len(parts) < 5:
            return
        complaint_id = int(parts[2])
        order_id = int(parts[3])
        worker_telegram_id = int(parts[4])

        async with async_session_factory() as session:
            order = await get_order_by_id(session, order_id)
            if not order:
                await callback.message.edit_text("Buyurtma topilmadi")
                return

            worker_username = order.assigned_username or "Ishchi"
            cemetery = order.grave.cemetery if order.grave else (order.cemetery.name if order.cemetery else "—")
            deceased = order.grave.deceased_full_name if order.grave else (order.deceased_full_name or "—")
            reason = order.feedback_reason or "Sabab ko'rsatilmagan"

            # Update complaint status
            from sqlalchemy import select
            from bot.database.models import Complaint, COMPLAINT_STATUS_RECLEANING
            result = await session.execute(
                select(Complaint).where(Complaint.id == complaint_id)
            )
            complaint = result.scalar_one_or_none()
            if complaint:
                complaint.status = COMPLAINT_STATUS_RECLEANING
                await session.commit()

        # Send to worker
        try:
            main_session = AiohttpSession()
            main_session._connector_init["family"] = socket.AF_INET
            main_bot = Bot(
                token=BOT_TOKEN,
                session=main_session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

            worker_buttons = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔁 Qayta tozalashni qabul qilish",
                            callback_data=f"reclean:accept:{order_id}:{worker_telegram_id}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Bekor qilish",
                            callback_data=f"reclean:cancel:{order_id}",
                        ),
                    ],
                ]
            )

            await main_bot.send_message(
                chat_id=worker_telegram_id,
                text=f"⚠️ <b>QAYTA TOZALASH SO'ROVI</b>\n\n"
                     f"📋 Buyurtma: #{order_id}\n"
                     f"🏛 Qabriston: {cemetery}\n"
                     f"🪦 Marhum: {deceased}\n\n"
                     f"📝 Mijoz shikoyati:\n{reason}\n\n"
                     f"Qayta tozalaysizmi?",
                reply_markup=worker_buttons,
            )

            await main_bot.session.close()
        except Exception as e:
            logger.error(f"Failed to send reclean request to worker: {e}")

        await callback.message.edit_text(
            callback.message.text + "\n\n✅ Ishchiga qayta tozalash so'rovi yuborildi"
        )


@verification_router.message(F.text)
async def admin_response_text(message: Message) -> None:
    """Receive admin response text and send to user."""
    admin_id = message.from_user.id

    if admin_id not in _admin_response_state:
        return

    state_data = _admin_response_state.pop(admin_id)
    complaint_id = state_data["complaint_id"]
    user_id = state_data["user_id"]
    response_text = message.text.strip()

    # Update complaint in database
    async with async_session_factory() as session:
        from sqlalchemy import select
        from bot.database.models import Complaint, COMPLAINT_STATUS_RESOLVED
        result = await session.execute(
            select(Complaint).where(Complaint.id == complaint_id)
        )
        complaint = result.scalar_one_or_none()
        if complaint:
            complaint.admin_response = response_text
            complaint.status = COMPLAINT_STATUS_RESOLVED
            await session.commit()

    # Send to user via main bot
    try:
        main_session = AiohttpSession()
        main_session._connector_init["family"] = socket.AF_INET
        main_bot = Bot(
            token=BOT_TOKEN,
            session=main_session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        await main_bot.send_message(
            chat_id=user_id,
            text=f"📬 <b>Admin javobi:</b>\n\n{response_text}",
        )

        await main_bot.session.close()
    except Exception as e:
        logger.error(f"Failed to send response to user: {e}")

    await message.answer("✅ Javob mijozga yuborildi!")


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



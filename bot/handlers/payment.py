"""
Payment flow: select method, upload receipt screenshot.
"""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize

logger = logging.getLogger(__name__)

from bot.database.analytics import (
    track_event,
    EVENT_CHECKOUT_START,
    EVENT_PAYMENT_METHOD,
    EVENT_PAYMENT_RECEIPT,
    EVENT_PAYMENT_CONFIRMED,
)
from bot.database.db import async_session_factory
from bot.database.queries import (
    get_order_by_id,
    get_regions,
    get_user_by_telegram_id,
    update_order_receipt,
    update_order_status,
    list_user_graves,
    get_grave_by_id,
    update_order_grave,
)
from bot.keyboards.inline import (
    grave_regions_inline,
    payment_methods_inline,
    receipt_confirm_reject_inline,
    receipt_verify_inline,
    select_grave_for_order_inline,
)
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.helpers import format_price
from bot.utils.telegram_helpers import safe_edit_text
from bot_config import (
    ADMIN_IDS,
    PAYMENT_CARD_NUMBER,
    PAYMENT_CARD_INTERNAL,
    PAYMENT_CARD_INTERNATIONAL,
    PAYMENT_CHANNEL_ID,
    PAYMENT_GROUP_ID,
    PAYMENT_BOT_TOKEN,
    TELEGRAM_GROUP,
)
from bot.utils.texts import get_text
from bot.database.models import ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED
from bot.states.forms import GraveState, PaymentState
from apps.botapp.helpers import get_user_language as _get_lang

router = Router(name="payment")


async def show_payment_options(callback: CallbackQuery, order_id: int, lang: str) -> None:
    """Show grave selection first, then payment method. Called after order creation."""
    # Track checkout start
    await track_event(callback.from_user.id, EVENT_CHECKOUT_START, {"order_id": order_id})

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await callback.message.answer(get_text(lang, "cart_empty"))
            return

        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            return

        graves = await list_user_graves(session, user.id)

    total_str = format_price(order.total_price, lang)

    # Show grave selection first
    text = (
        get_text(lang, "payment_title")
        + "\n\n"
        + get_text(lang, "order_placed", order_id=order.id, total=total_str)
        + "\n\n"
        + get_text(lang, "select_grave_for_order")
    )
    await safe_edit_text(
        callback,
        text,
        reply_markup=select_grave_for_order_inline(graves, lang, order_id),
    )


# -----------------------------------------------------------------------------
# Grave selection for payment (callback)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("pay:grave:"))
async def payment_grave_selected_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected a grave for the order. Show payment methods."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    order_id = int(parts[2])
    grave_id = int(parts[3])
    lang = await _get_lang(callback.from_user.id)

    # Save selected grave
    await state.update_data(payment_order_id=order_id, selected_grave_id=grave_id)

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        grave = None
        if user:
            grave = await get_grave_by_id(session, grave_id, user.id)
            # Save grave_id to order
            await update_order_grave(session, order_id, grave_id)
            await session.commit()

    if not order:
        return

    total_str = format_price(order.total_price, lang)

    # Show grave info and payment methods
    grave_info = ""
    if grave:
        grave_info = f"\n🪦 {grave.deceased_full_name or '—'}\n📍 {grave.cemetery or '—'}\n\n"

    text = (
        get_text(lang, "payment_title")
        + "\n\n"
        + get_text(lang, "order_placed", order_id=order.id, total=total_str)
        + grave_info
        + get_text(lang, "payment_select_method")
    )
    await safe_edit_text(
        callback,
        text,
        reply_markup=payment_methods_inline(lang, order_id),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("pay:newgrave:"))
async def payment_new_grave_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to add a new grave for this order. Start grave FSM."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    order_id = int(parts[2])
    lang = await _get_lang(callback.from_user.id)

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        order = await get_order_by_id(session, order_id)
        if not user or not order or order.user_id != user.id:
            await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
            return
        regions = await get_regions(session)

    await state.set_state(GraveState.region)
    await state.update_data(
        lang=lang,
        payment_order_id=order_id,
        return_to_payment=True,
    )
    await safe_edit_text(callback, get_text(lang, "add_grave_first"))
    await callback.message.answer(
        get_text(lang, "grave_enter_region"),
        reply_markup=grave_regions_inline(regions, lang),
    )


# -----------------------------------------------------------------------------
# Payment method selection (callback)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("pay:method:"))
async def payment_method_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Show card number (easy copy) and ask for receipt upload."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    order_id = int(parts[2])
    method = parts[3]  # "internal" or "visa"
    lang = await _get_lang(callback.from_user.id)

    # Track payment method selection
    await track_event(callback.from_user.id, EVENT_PAYMENT_METHOD, {"method": method, "order_id": order_id})

    data = await state.get_data()
    grave_id = data.get("selected_grave_id")

    await state.update_data(payment_order_id=order_id, payment_method=method, selected_grave_id=grave_id)
    await state.set_state(PaymentState.upload_receipt)

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
    if not order:
        return
    if not grave_id:
        grave_id = order.grave_id
    total_str = format_price(order.total_price, lang)

    # Select card and info text based on payment method
    if method == "internal":
        card_raw = PAYMENT_CARD_INTERNAL if PAYMENT_CARD_INTERNAL else PAYMENT_CARD_NUMBER or "—"
        card_info_key = "payment_internal_card_info"
    else:  # visa
        card_raw = PAYMENT_CARD_INTERNATIONAL if PAYMENT_CARD_INTERNATIONAL else PAYMENT_CARD_NUMBER or "—"
        card_info_key = "payment_visa_card_info"

    # Format card for easy copy (remove spaces)
    card_copy = card_raw.replace(" ", "")

    text = (
        get_text(lang, "payment_title")
        + "\n\n"
        + get_text(lang, "order_placed", order_id=order.id, total=total_str)
        + "\n\n"
        + get_text(lang, card_info_key)
        + f"\n\n<code>{card_copy}</code>\n\n"
        + get_text(lang, "payment_send_receipt")
    )
    await safe_edit_text(callback, text)


# -----------------------------------------------------------------------------
# Receipt upload (photo)
# -----------------------------------------------------------------------------


@router.message(PaymentState.upload_receipt, F.photo)
async def payment_receipt_upload(message: Message, state: FSMContext) -> None:
    """Receive receipt screenshot - simplified version."""
    data = await state.get_data()
    order_id = data.get("payment_order_id")
    method = data.get("payment_method", "card")
    grave_id = data.get("selected_grave_id")

    lang = await _get_lang(message.from_user.id)

    if not order_id:
        await state.clear()
        await message.answer(get_text(lang, "cart_empty"))
        return

    # Get largest photo file_id
    photo: PhotoSize = message.photo[-1]
    file_id = photo.file_id

    grave = None
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await state.clear()
            return

        order = await get_order_by_id(session, order_id)
        if not order or order.user_id != user.id:
            await message.answer(get_text(lang, "cart_empty"))
            await state.clear()
            return

        if not grave_id:
            grave_id = order.grave_id

        # Get grave info if selected or already attached to order
        if grave_id:
            grave = await get_grave_by_id(session, grave_id, user.id)

        await update_order_receipt(session, order_id, file_id, method)
        await session.commit()

    # Track receipt upload
    await track_event(message.from_user.id, EVENT_PAYMENT_RECEIPT, {"order_id": order_id})

    await state.clear()

    # Payment method label
    method_label = "Humo/Uzcard" if method == "internal" else "Visa"

    # Grave info for caption
    grave_info = ""
    if grave:
        grave_info = (
            f"\n🪦 {grave.deceased_full_name or '—'}\n"
            f"   📍 {grave.cemetery or '—'}"
        )

    # User contact info
    username = f"@{message.from_user.username}" if message.from_user.username else "—"

    # Build caption
    caption = (
        f"💳 To'lov cheki\n\n"
        f"📋 Buyurtma: #{order.id}\n"
        f"👤 {user.full_name or '—'}\n"
        f"📞 {user.phone_number or '—'}\n"
        f"📱 {username}\n"
        f"💰 {format_price(order.total_price, lang)}\n"
        f"💳 {method_label}"
        f"{grave_info}"
    )

    # Send receipt to BOT_TOKEN3 with True/False buttons
    if PAYMENT_BOT_TOKEN:
        try:
            from aiogram import Bot
            from aiogram.types import BufferedInputFile

            verification_bot = Bot(token=PAYMENT_BOT_TOKEN)

            # Download photo and send via verification bot
            file = await message.bot.get_file(file_id)
            file_bytes = await message.bot.download_file(file.file_path)

            # Send to each admin
            for admin_id in ADMIN_IDS:
                try:
                    file_bytes.seek(0)
                    await verification_bot.send_photo(
                        chat_id=admin_id,
                        photo=BufferedInputFile(file_bytes.read(), filename="receipt.jpg"),
                        caption=caption,
                        reply_markup=receipt_verify_inline(order_id, message.from_user.id, grave_id or 0),
                    )
                    logger.info(f"Receipt sent to admin {admin_id} via BOT_TOKEN3")
                except Exception as e:
                    logger.error(f"Failed to send to admin {admin_id}: {e}")

            await verification_bot.session.close()
        except Exception as e:
            logger.error(f"Failed to send receipt via BOT_TOKEN3: {e}")

    await message.answer(
        get_text(lang, "payment_receipt_received"),
        reply_markup=main_menu_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# Admin: Confirm / Reject receipt (pay:confirm, pay:reject)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("pay:confirm:"))
async def payment_confirm_callback(callback: CallbackQuery) -> None:
    """Admin confirms receipt: send to channel, update order to paid."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(get_text("uz", "cart_empty"), show_alert=True)
        return
    order_id = int(callback.data.replace("pay:confirm:", ""))
    lang = await _get_lang(callback.from_user.id)
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order or not order.receipt_file_id:
            await callback.answer("Buyurtma topilmadi", show_alert=True)
            return
        await update_order_status(session, order_id, ORDER_STATUS_PAID)
        await session.commit()

        # Track payment confirmed for the user who placed the order
        if order.user:
            await track_event(order.user.telegram_id, EVENT_PAYMENT_CONFIRMED, {"order_id": order_id})

    # Send to channel
    if PAYMENT_CHANNEL_ID:
        try:
            channel_id = int(PAYMENT_CHANNEL_ID)
            caption = (
                f"✅ Tasdiqlangan to'lov\n\n"
                f"📋 Buyurtma #{order.id}\n"
                f"👤 {order.full_name or '—'}\n"
                f"📞 {order.phone_number or '—'}\n"
                f"💰 Jami: {format_price(order.total_price, lang)}"
            )
            await callback.bot.send_photo(
                chat_id=channel_id,
                photo=order.receipt_file_id,
                caption=caption,
            )
        except (ValueError, Exception):
            pass
    # Notify user
    if order.user:
        user_lang = order.user.language or "uz"
        try:
            await callback.bot.send_message(
                chat_id=order.user.telegram_id,
                text=get_text(user_lang, "payment_confirmed", order_id=order.id),
            )
        except Exception:
            pass
    await callback.answer("Tasdiqlandi")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.callback_query(lambda c: c.data and c.data.startswith("pay:reject:"))
async def payment_reject_callback(callback: CallbackQuery) -> None:
    """Admin rejects receipt: update order to cancelled, notify user."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(get_text("uz", "cart_empty"), show_alert=True)
        return
    order_id = int(callback.data.replace("pay:reject:", ""))
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        await update_order_status(session, order_id, ORDER_STATUS_CANCELLED)
        await session.commit()
    # Notify user
    if order and order.user:
        user_lang = order.user.language or "uz"
        try:
            await callback.bot.send_message(
                chat_id=order.user.telegram_id,
                text=get_text(user_lang, "payment_rejected", order_id=order.id),
            )
        except Exception:
            pass
    await callback.answer("Rad etildi")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

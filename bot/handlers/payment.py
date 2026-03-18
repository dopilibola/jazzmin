"""
Payment flow: select method, upload receipt screenshot.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize

from bot.database.db import async_session_factory
from bot.database.queries import (
    get_order_by_id,
    get_user_by_telegram_id,
    update_order_receipt,
    update_order_status,
)
from bot.keyboards.inline import payment_methods_inline, receipt_confirm_reject_inline
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.helpers import format_price
from bot.utils.telegram_helpers import safe_edit_text
from bot_config import ADMIN_IDS, PAYMENT_CARD_NUMBER, PAYMENT_CHANNEL_ID, PAYMENT_GROUP_ID
from bot.utils.texts import get_text
from bot.database.models import ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED
from bot.states.forms import PaymentState
from apps.botapp.helpers import get_user_language as _get_lang

router = Router(name="payment")


async def show_payment_options(callback: CallbackQuery, order_id: int, lang: str) -> None:
    """Show payment method selection. Called after order creation."""
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
    if not order:
        await callback.message.answer(get_text(lang, "cart_empty"))
        return
    total_str = format_price(order.total_price, lang)
    text = (
        get_text(lang, "payment_title")
        + "\n\n"
        + get_text(lang, "order_placed", order_id=order.id, total=total_str)
        + "\n\n"
        + get_text(lang, "payment_select_method")
    )
    await safe_edit_text(
        callback,
        text,
        reply_markup=payment_methods_inline(lang, order_id),
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
    method = parts[3]
    lang = await _get_lang(callback.from_user.id)
    await state.update_data(payment_order_id=order_id, payment_method=method)
    await state.set_state(PaymentState.upload_receipt)
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
    if not order:
        return
    total_str = format_price(order.total_price, lang)
    card_display = PAYMENT_CARD_NUMBER if PAYMENT_CARD_NUMBER else "—"
    text = (
        get_text(lang, "payment_title")
        + "\n\n"
        + get_text(lang, "order_placed", order_id=order.id, total=total_str)
        + "\n\n"
        + get_text(lang, "payment_card_info")
        + f"\n\n<code>{card_display}</code>\n\n"
        + get_text(lang, "payment_send_receipt")
    )
    await safe_edit_text(callback, text)


# -----------------------------------------------------------------------------
# Receipt upload (photo)
# -----------------------------------------------------------------------------


@router.message(PaymentState.upload_receipt, F.photo)
async def payment_receipt_upload(message: Message, state: FSMContext) -> None:
    """Receive receipt screenshot."""
    data = await state.get_data()
    order_id = data.get("payment_order_id")
    method = data.get("payment_method")
    if not order_id or not method:
        await state.clear()
        return
    # Get largest photo file_id
    photo: PhotoSize = message.photo[-1]
    file_id = photo.file_id
    lang = await _get_lang(message.from_user.id)
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        order = await get_order_by_id(session, order_id)
        if not order or order.user_id != user.id:
            await message.answer(get_text(lang, "cart_empty"))
            await state.clear()
            return
        await update_order_receipt(session, order_id, file_id, method)
        await session.commit()
    await state.clear()
    # Forward receipt to payment group with confirm/reject buttons
    if PAYMENT_GROUP_ID:
        try:
            group_id = int(PAYMENT_GROUP_ID)
            caption = (
                f"💳 To'lov kvitansiyasi\n\n"
                f"📋 Buyurtma #{order.id}\n"
                f"👤 {user.full_name or '—'}\n"
                f"📞 {user.phone_number or '—'}\n"
                f"💰 Jami: {format_price(order.total_price, lang)}\n"
                f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else ''}"
            )
            await message.bot.send_photo(
                chat_id=group_id,
                photo=file_id,
                caption=caption,
                reply_markup=receipt_confirm_reject_inline(lang, order_id),
            )
        except (ValueError, Exception):
            pass
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

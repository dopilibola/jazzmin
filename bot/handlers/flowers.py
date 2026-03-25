"""
Flowers section: list flowers, order.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from apps.botapp.helpers import (
    format_price,
    get_active_flowers,
    get_flower_by_pk,
    get_user_language as _get_lang,
)
from bot.database.analytics import track_event, EVENT_FLOWERS_VIEW, EVENT_FLOWER_ORDER
from bot.database.db import async_session_factory
from bot.database.queries import get_user_by_telegram_id
from bot.keyboards.inline import flowers_list_inline
from bot.keyboards.reply import back_to_main_keyboard
from bot.utils.texts import get_text, get_all_button_texts

router = Router(name="flowers")

FLOWERS_BUTTON_TEXTS = get_all_button_texts("btn_flowers")


async def _build_flowers_text(lang: str):
    """Fetch active flowers from Django DB and build display text + list."""
    flowers = await get_active_flowers()
    if not flowers:
        return None, None
    text = get_text(lang, "flower_menu_title") + "\n\n"
    for f in flowers:
        # Icon based on type
        icon = "🌱" if f.is_plantable else "💐"
        text += f"{icon} <b>{f.name}</b>\n"

        # Price breakdown
        text += f"   💰 Narxi: {format_price(f.price, lang)}\n"
        if f.delivery_fee:
            text += f"   🚚 Dastafka: {format_price(f.delivery_fee, lang)}\n"
        if f.is_plantable and f.planting_fee:
            text += f"   🌱 Ekish: {format_price(f.planting_fee, lang)}\n"

        # Total
        text += f"   ✅ <b>Jami: {format_price(f.total_price, lang)}</b>\n"

        desc = (f.description or "")[:80]
        if desc:
            text += f"   {desc}\n"
        text += "\n"
    return text, flowers


async def _send_flowers_content(message: Message, lang: str) -> None:
    """Send flowers list with inline buttons + back keyboard."""
    kb = back_to_main_keyboard(lang)
    text, flowers = await _build_flowers_text(lang)
    if not flowers:
        await message.answer(
            get_text(lang, "flower_menu_title") + "\n\n" + get_text(lang, "cart_empty"),
            reply_markup=kb,
        )
        return
    await message.answer(
        text,
        reply_markup=flowers_list_inline(flowers, lang, add_back=False),
    )


@router.message(F.text.in_(FLOWERS_BUTTON_TEXTS))
async def show_flowers(message: Message) -> None:
    """Flowers pressed: show flower list + back button."""
    lang = await _get_lang(message.from_user.id)

    # Track flowers view
    await track_event(message.from_user.id, EVENT_FLOWERS_VIEW)

    await message.answer("⬇️", reply_markup=back_to_main_keyboard(lang))
    await _send_flowers_content(message, lang)


@router.callback_query(lambda c: c.data and c.data == "fl:main")
async def flowers_main_callback(callback: CallbackQuery) -> None:
    """Back to flowers list."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    text, flowers = await _build_flowers_text(lang)
    if not flowers:
        await callback.message.edit_text(
            get_text(lang, "flower_menu_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    await callback.message.edit_text(
        text,
        reply_markup=flowers_list_inline(flowers, lang, add_back=False),
    )


@router.callback_query(lambda c: c.data and c.data == "nav:continue:flowers")
async def continue_shopping_flowers_callback(callback: CallbackQuery) -> None:
    """Handle 'Continue Shopping' from notification."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    text, flowers = await _build_flowers_text(lang)
    if not flowers:
        await callback.message.edit_text(
            get_text(lang, "flower_menu_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    await callback.message.edit_text(
        text,
        reply_markup=flowers_list_inline(flowers, lang, add_back=False),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("fl:order:"))
async def flower_order_callback(callback: CallbackQuery) -> None:
    """Create flower order immediately with user data, redirect to payment."""
    await callback.answer()
    flower_id = int(callback.data.replace("fl:order:", ""))
    telegram_id = callback.from_user.id
    lang = await _get_lang(telegram_id)

    # Track flower order
    await track_event(telegram_id, EVENT_FLOWER_ORDER, {"flower_id": flower_id})

    flower = await get_flower_by_pk(flower_id)
    if not flower:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user or not user.full_name or not user.phone_number:
            await callback.answer(get_text(lang, "registration_required"), show_alert=True)
            return
        from bot.database.queries import create_order_from_flower

        order = await create_order_from_flower(
            session,
            user.id,
            flower_id,
            flower.name,
            int(flower.total_price),  # Jami: narx + dastafka + ekish
            full_name=user.full_name,
            phone_number=user.phone_number,
        )
        await session.commit()

    from bot.handlers.payment import show_payment_options

    await show_payment_options(callback, order.id, lang)

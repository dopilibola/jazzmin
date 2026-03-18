"""
Checkout flow: collect full name, phone, region, district, cemetery, deceased info, comment.
Then create order and proceed to payment.
"""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import async_session_factory
from bot.database.queries import (
    create_order_from_cart,
    get_cemeteries_by_district,
    get_districts_by_region,
    get_flower_cart_items,
    get_regions,
    get_user_by_telegram_id,
)
from bot.keyboards.inline import (
    order_cemeteries_inline,
    order_confirm_inline,
    order_districts_inline,
    order_regions_inline,
)
from bot.keyboards.reply import cancel_keyboard, main_menu_keyboard, phone_keyboard
from bot.utils.helpers import format_price
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_full_name, is_valid_year

from bot.states.forms import CheckoutState
from apps.botapp.helpers import get_user_language as _get_lang

router = Router(name="checkout")


# -----------------------------------------------------------------------------
# Start checkout from cart
# -----------------------------------------------------------------------------


async def _start_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """Start checkout from cart (flower cart). Collect full name first."""
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
            return
        items = await get_flower_cart_items(session, user.id)
    if not items:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return
    await state.set_state(CheckoutState.full_name)
    await state.update_data(user_id=user.id)
    await safe_edit_text(callback, get_text(lang, "order_enter_full_name"))
    await callback.message.answer("👇", reply_markup=cancel_keyboard(lang))


# -----------------------------------------------------------------------------
# Checkout form steps (FSM) - flower cart only
# -----------------------------------------------------------------------------


def _is_cancel(text: str, lang: str) -> bool:
    """Check if user pressed cancel."""
    t = (text or "").strip()
    return t in (get_text("en", "btn_cancel"), get_text("ru", "btn_cancel"), get_text("uz", "btn_cancel")) or t.lower() in ("/cancel", "cancel")


@router.message(CheckoutState.full_name, F.text)
async def checkout_full_name(message: Message, state: FSMContext) -> None:
    """Receive full name."""
    lang = await _get_lang(message.from_user.id)
    if _is_cancel(message.text or "", lang):
        await state.clear()
        await message.answer(get_text(lang, "order_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return
    await state.update_data(full_name=(message.text or "").strip())
    await state.set_state(CheckoutState.phone_number)
    await message.answer(get_text(lang, "order_enter_phone"), reply_markup=phone_keyboard(lang))


@router.message(CheckoutState.phone_number, F.contact)
async def checkout_phone_contact(message: Message, state: FSMContext) -> None:
    """Receive phone from contact share."""
    phone = message.contact.phone_number if message.contact else ""
    if not phone:
        return
    await state.update_data(phone_number=phone)
    await state.set_state(CheckoutState.region)
    lang = await _get_lang(message.from_user.id)
    async with async_session_factory() as session:
        regions = await get_regions(session)
    await message.answer(
        get_text(lang, "order_select_region"),
        reply_markup=order_regions_inline(regions, lang),
    )


@router.message(CheckoutState.phone_number, F.text)
async def checkout_phone_text(message: Message, state: FSMContext) -> None:
    """Receive phone as text (fallback)."""
    lang = await _get_lang(message.from_user.id)
    phone = (message.text or "").strip().replace(" ", "").replace("-", "")
    if len(phone) < 9:
        await message.answer(get_text(lang, "invalid_phone"))
        return
    await state.update_data(phone_number=phone)
    await state.set_state(CheckoutState.region)
    async with async_session_factory() as session:
        regions = await get_regions(session)
    await message.answer(
        get_text(lang, "order_select_region"),
        reply_markup=order_regions_inline(regions, lang),
    )


# -----------------------------------------------------------------------------
# Region, District, Cemetery (callbacks)
# -----------------------------------------------------------------------------


@router.callback_query(CheckoutState.region, lambda c: c.data and c.data.startswith("ord:"))
async def checkout_region_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "ord:cancel":
        await state.clear()
        await safe_edit_text(callback, get_text(lang, "order_cancelled"))
        await callback.message.answer(reply_markup=main_menu_keyboard(lang))
        return
    if data.startswith("ord:region:"):
        region_id = int(data.replace("ord:region:", ""))
        await state.update_data(region_id=region_id)
        await state.set_state(CheckoutState.district)
        async with async_session_factory() as session:
            districts = await get_districts_by_region(session, region_id)
        await safe_edit_text(
            callback,
            get_text(lang, "order_select_district"),
            reply_markup=order_districts_inline(districts, lang),
        )


@router.callback_query(CheckoutState.district, lambda c: c.data and c.data.startswith("ord:"))
async def checkout_district_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "ord:back:district":
        await state.set_state(CheckoutState.region)
        async with async_session_factory() as session:
            regions = await get_regions(session)
        await safe_edit_text(
            callback,
            get_text(lang, "order_select_region"),
            reply_markup=order_regions_inline(regions, lang),
        )
        return
    if data.startswith("ord:district:"):
        district_id = int(data.replace("ord:district:", ""))
        await state.update_data(district_id=district_id)
        await state.set_state(CheckoutState.cemetery)
        async with async_session_factory() as session:
            cemeteries = await get_cemeteries_by_district(session, district_id)
        await safe_edit_text(
            callback,
            get_text(lang, "order_select_cemetery"),
            reply_markup=order_cemeteries_inline(cemeteries, lang),
        )


@router.callback_query(CheckoutState.cemetery, lambda c: c.data and c.data.startswith("ord:"))
async def checkout_cemetery_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "ord:back:cemetery":
        form_data = await state.get_data()
        region_id = form_data.get("region_id")
        await state.set_state(CheckoutState.district)
        async with async_session_factory() as session:
            districts = await get_districts_by_region(session, region_id)
        await safe_edit_text(
            callback,
            get_text(lang, "order_select_district"),
            reply_markup=order_districts_inline(districts, lang),
        )
        return
    if data.startswith("ord:cemetery:"):
        cemetery_id = int(data.replace("ord:cemetery:", ""))
        await state.update_data(cemetery_id=cemetery_id)
        await state.set_state(CheckoutState.deceased_full_name)
        await safe_edit_text(callback, get_text(lang, "order_enter_deceased"))


# -----------------------------------------------------------------------------
# Deceased, birth year, death year, comment
# -----------------------------------------------------------------------------


@router.message(CheckoutState.deceased_full_name, F.text)
async def checkout_deceased(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return
    await state.update_data(deceased_full_name=(message.text or "").strip())
    await state.set_state(CheckoutState.birth_year)
    await message.answer(get_text(lang, "order_enter_birth_year"))


@router.message(CheckoutState.birth_year, F.text)
async def checkout_birth_year(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    if not is_valid_year(message.text or ""):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(birth_year=int((message.text or "").strip()))
    await state.set_state(CheckoutState.death_year)
    await message.answer(get_text(lang, "order_enter_death_year"))


@router.message(CheckoutState.death_year, F.text)
async def checkout_death_year(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    if not is_valid_year(message.text or ""):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(death_year=int((message.text or "").strip()))
    await state.set_state(CheckoutState.comment)
    await message.answer(get_text(lang, "order_enter_comment"))


@router.message(CheckoutState.comment, F.text)
async def checkout_comment(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    text = (message.text or "").strip()
    if text.lower() in ("/skip", "skip"):
        text = ""
    await state.update_data(comment=text[:500] if text else None)
    await state.set_state(CheckoutState.confirm)
    # Build summary
    data = await state.get_data()
    async with async_session_factory() as session:
        from bot.database.queries import (
            get_cemetery_by_id,
            get_district_by_id,
            get_region_by_id,
        )

        region = await get_region_by_id(session, data.get("region_id"))
        district = await get_district_by_id(session, data.get("district_id"))
        cemetery = await get_cemetery_by_id(session, data.get("cemetery_id"))
        items = await get_flower_cart_items(session, data["user_id"])
        services_str = "\n".join(f"  • {i.title} x{i.quantity}" for i in items)
        total = sum(i.quantity * i.price for i in items)
    region_name = region.get_name(lang) if region else ""
    district_name = district.get_name(lang) if district else ""
    cemetery_name = cemetery.name if cemetery else ""
    total_str = format_price(total, lang)
    summary = get_text(
        lang,
        "order_confirm_summary",
        region=region_name,
        district=district_name,
        cemetery=cemetery_name,
        deceased=data.get("deceased_full_name", ""),
        birth_year=data.get("birth_year", ""),
        death_year=data.get("death_year", ""),
        services=services_str,
        total=total_str,
    )
    await message.answer(
        get_text(lang, "order_confirm_title") + "\n\n" + summary,
        reply_markup=order_confirm_inline(lang),
    )


# -----------------------------------------------------------------------------
# Confirm order -> create order -> payment
# -----------------------------------------------------------------------------


@router.callback_query(CheckoutState.confirm, lambda c: c.data and c.data.startswith("ord:"))
async def checkout_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "ord:cancel":
        await state.clear()
        await safe_edit_text(callback, get_text(lang, "order_cancelled"))
        await callback.message.answer(reply_markup=main_menu_keyboard(lang))
        return
    if data == "ord:confirm":
        form_data = await state.get_data()
        async with async_session_factory() as session:
            items = await get_flower_cart_items(session, form_data["user_id"])
            order = await create_order_from_cart(
                session,
                form_data["user_id"],
                items,
                full_name=form_data.get("full_name", ""),
                phone_number=form_data.get("phone_number", ""),
                region_id=form_data.get("region_id"),
                district_id=form_data.get("district_id"),
                cemetery_id=form_data.get("cemetery_id"),
                deceased_full_name=form_data.get("deceased_full_name"),
                birth_year=form_data.get("birth_year"),
                death_year=form_data.get("death_year"),
                comment=form_data.get("comment"),
            )
            await session.commit()
        await state.clear()
        if order:
            # Redirect to payment
            from bot.handlers.payment import show_payment_options

            await show_payment_options(callback, order.id, lang)
        else:
            await safe_edit_text(callback, get_text(lang, "cart_empty"))
            await callback.message.answer(reply_markup=main_menu_keyboard(lang))

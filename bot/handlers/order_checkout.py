"""
Order checkout flow: collect region, district, cemetery, deceased info.
Triggered from cart Place Order.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import async_session_factory
from bot.database.queries import (
    create_order_from_cart,
    get_cemeteries_by_district,
    get_districts_by_region,
    get_or_create_cart,
    get_regions,
    get_user_by_telegram_id,
)
from bot.keyboards.inline import (
    order_cemeteries_inline,
    order_confirm_inline,
    order_districts_inline,
    order_regions_inline,
)
from bot.keyboards.reply import main_menu_keyboard
from bot.services.cart_logic import format_cart_for_display, get_cart_total
from bot.states.forms import OrderCheckoutState
from bot.utils.services_catalog import format_price, get_service, get_service_name
from bot.utils.texts import get_text
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.validators import is_valid_full_name, is_valid_year

router = Router(name="order_checkout")


async def _get_lang(telegram_id: int) -> str:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


# -----------------------------------------------------------------------------
# Start checkout from cart (cart:checkout)
# -----------------------------------------------------------------------------


async def _start_checkout(callback: CallbackQuery, state: FSMContext) -> bool:
    """Start order checkout. Returns True if started."""
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
            return False
        cart = await get_or_create_cart(session, user.id)
        items = list(cart.items)  # Access while session is active
    if not items:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return False
    await state.set_state(OrderCheckoutState.region)
    await state.update_data(cart_user_id=user.id)
    async with async_session_factory() as session:
        regions = await get_regions(session)
    await safe_edit_text(
        callback,
        get_text(lang, "order_select_region"),
        reply_markup=order_regions_inline(regions, lang),
    )
    return True


# -----------------------------------------------------------------------------
# Region, District, Cemetery (callbacks)
# -----------------------------------------------------------------------------


@router.callback_query(OrderCheckoutState.region, lambda c: c.data and c.data.startswith("ord:"))
async def order_region_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
        await state.set_state(OrderCheckoutState.district)
        async with async_session_factory() as session:
            districts = await get_districts_by_region(session, region_id)
        await safe_edit_text(
            callback,
            get_text(lang, "order_select_district"),
            reply_markup=order_districts_inline(districts, lang),
        )


@router.callback_query(OrderCheckoutState.district, lambda c: c.data and c.data.startswith("ord:"))
async def order_district_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "ord:back:district":
        await state.set_state(OrderCheckoutState.region)
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
        await state.set_state(OrderCheckoutState.cemetery)
        async with async_session_factory() as session:
            cemeteries = await get_cemeteries_by_district(session, district_id)
        await safe_edit_text(
            callback,
            get_text(lang, "order_select_cemetery"),
            reply_markup=order_cemeteries_inline(cemeteries, lang),
        )


@router.callback_query(OrderCheckoutState.cemetery, lambda c: c.data and c.data.startswith("ord:"))
async def order_cemetery_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "ord:back:cemetery":
        data = await state.get_data()
        region_id = data.get("region_id")
        await state.set_state(OrderCheckoutState.district)
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
        await state.set_state(OrderCheckoutState.deceased_full_name)
        await safe_edit_text(callback, get_text(lang, "order_enter_deceased"))


# -----------------------------------------------------------------------------
# Deceased name, birth year, death year (messages)
# -----------------------------------------------------------------------------


@router.message(OrderCheckoutState.deceased_full_name, F.text)
async def order_deceased_name(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return
    await state.update_data(deceased_full_name=(message.text or "").strip())
    await state.set_state(OrderCheckoutState.birth_year)
    await message.answer(get_text(lang, "order_enter_birth_year"))


@router.message(OrderCheckoutState.birth_year, F.text)
async def order_birth_year(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    if not is_valid_year(message.text or ""):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(birth_year=int((message.text or "").strip()))
    await state.set_state(OrderCheckoutState.death_year)
    await message.answer(get_text(lang, "order_enter_death_year"))


@router.message(OrderCheckoutState.death_year, F.text)
async def order_death_year(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message.from_user.id)
    if not is_valid_year(message.text or ""):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(death_year=int((message.text or "").strip()))
    await state.set_state(OrderCheckoutState.confirm)
    # Build summary
    data = await state.get_data()
    async with async_session_factory() as session:
        from bot.database.queries import (
            get_cemetery_by_id,
            get_district_by_id,
            get_region_by_id,
        )

        region = await get_region_by_id(session, data["region_id"])
        district = await get_district_by_id(session, data["district_id"])
        cemetery = await get_cemetery_by_id(session, data["cemetery_id"])
        cart = await get_or_create_cart(session, data["cart_user_id"])
        items = list(cart.items)  # Access while session is active
        services_lines = []
        for item in items:
            svc = get_service(item.service_id)
            name = get_service_name(svc, lang) if svc else item.service_id
            services_lines.append(f"  • {name} x{item.quantity}")
        total_str = format_price(get_cart_total(cart), lang)
    region_name = region.get_name(lang) if region else ""
    district_name = district.get_name(lang) if district else ""
    cemetery_name = cemetery.name if cemetery else ""
    services_str = "\n".join(services_lines)
    summary = get_text(
        lang,
        "order_confirm_summary",
        region=region_name,
        district=district_name,
        cemetery=cemetery_name,
        deceased=data["deceased_full_name"],
        birth_year=data["birth_year"],
        death_year=data["death_year"],
        services=services_str,
        total=total_str,
    )
    await message.answer(
        get_text(lang, "order_confirm_title") + "\n\n" + summary,
        reply_markup=order_confirm_inline(lang),
    )


# -----------------------------------------------------------------------------
# Confirm or cancel
# -----------------------------------------------------------------------------


@router.callback_query(OrderCheckoutState.confirm, lambda c: c.data and c.data.startswith("ord:"))
async def order_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
            cart = await get_or_create_cart(session, form_data["cart_user_id"])
            order = await create_order_from_cart(
                session,
                form_data["cart_user_id"],
                cart,
                region_id=form_data.get("region_id"),
                district_id=form_data.get("district_id"),
                cemetery_id=form_data.get("cemetery_id"),
                deceased_full_name=form_data.get("deceased_full_name"),
                birth_year=form_data.get("birth_year"),
                death_year=form_data.get("death_year"),
            )
            await session.commit()
        await state.clear()
        if order:
            total_str = format_price(order.total, lang)
            await safe_edit_text(
                callback,
                get_text(lang, "order_placed", order_id=order.id, total=total_str),
            )
        await callback.message.answer(reply_markup=main_menu_keyboard(lang))

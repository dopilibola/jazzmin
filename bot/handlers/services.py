"""
Services section: list grave cleaning services, order.
All service data is fetched dynamically from Django Admin-managed database.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from apps.botapp.helpers import (
    format_price,
    get_active_services,
    get_service_by_pk,
    get_user_language as _get_lang,
)
from bot.database.db import async_session_factory
from bot.database.queries import (
    create_or_update_user,
    get_user_by_telegram_id,
)
from bot.keyboards.inline import services_list_inline
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.texts import get_text

router = Router(name="services")


async def _build_services_text(lang: str):
    """Fetch active services from Django DB and build display text + list."""
    services = await get_active_services()
    if not services:
        return None, None
    text = get_text(lang, "services_title") + "\n\n"
    for s in services:
        desc = (s.description or "")[:80]
        text += f"• {s.name} — {format_price(s.price, lang)}\n"
        if desc:
            text += f"  {desc}\n"
    return text, services


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_services"),
            get_text("ru", "btn_services"),
            get_text("uz", "btn_services"),
        ]
    )
)
async def show_services(message: Message) -> None:
    """Show cleaning services directly (no Flowers in Services)."""
    lang = await _get_lang(message.from_user.id)
    text, services = await _build_services_text(lang)
    if not services:
        await message.answer(
            get_text(lang, "services_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    await message.answer(
        text,
        reply_markup=services_list_inline(services, lang, add_back=False),
    )


@router.callback_query(lambda c: c.data and c.data == "svc:main")
async def services_main_callback(callback: CallbackQuery) -> None:
    """Back to services list (same as show_services)."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    text, services = await _build_services_text(lang)
    if not services:
        await callback.message.edit_text(
            get_text(lang, "services_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    await callback.message.edit_text(
        text,
        reply_markup=services_list_inline(services, lang, add_back=False),
    )


@router.callback_query(lambda c: c.data and c.data == "nav:continue:services")
async def continue_shopping_services_callback(callback: CallbackQuery) -> None:
    """Handle 'Continue Shopping' from add-to-cart notification (cleaning)."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    text, services = await _build_services_text(lang)
    if not services:
        await callback.message.edit_text(
            get_text(lang, "services_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    await callback.message.edit_text(
        text,
        reply_markup=services_list_inline(services, lang, add_back=False),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("svc:order:"))
async def service_order_callback(callback: CallbackQuery) -> None:
    """Create service order immediately with user data, redirect to payment."""
    await callback.answer()
    service_id = int(callback.data.replace("svc:order:", ""))
    telegram_id = callback.from_user.id
    lang = await _get_lang(telegram_id)

    service = await get_service_by_pk(service_id)
    if not service:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user or not user.full_name or not user.phone_number:
            await callback.answer(get_text(lang, "registration_required"), show_alert=True)
            return
        from bot.database.queries import create_order_from_service

        order = await create_order_from_service(
            session,
            user.id,
            service_id,
            service.name,
            int(service.price),
            full_name=user.full_name,
            phone_number=user.phone_number,
        )
        await session.commit()

    from bot.handlers.payment import show_payment_options

    await show_payment_options(callback, order.id, lang)

"""
Profile: view profile, update profile, profile menu (Profile, Add Grave, My Graves).
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import async_session_factory
from bot.database.queries import (
    create_or_update_user,
    get_orders_by_user,
    get_user_by_telegram_id,
    list_user_graves,
)
from bot.keyboards.inline import language_inline, profile_inline
from bot.keyboards.reply import main_menu_keyboard, phone_keyboard, profile_menu_keyboard
from bot.services.google_sheets import sync_user_to_sheet
from bot.states.forms import ProfileState
from bot.utils.helpers import format_grave_date, format_price
from bot.utils.texts import LANG_NAMES, get_status_label, get_text
from bot.utils.validators import is_valid_full_name, is_valid_phone, normalize_phone
from apps.botapp.helpers import get_user_language as _get_lang, save_user_profile
from bot_config import GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID

router = Router(name="profile")


def _format_order_list_item(order, lang: str) -> str:
    """Format order for list display."""
    status_label = get_status_label(lang, order.status)
    date_str = order.created_at.strftime("%d.%m.%Y") if order.created_at else ""
    total_str = format_price(getattr(order, "total_price", 0) or 0, lang)
    return (
        get_text(lang, "order_item", id=order.id, status=status_label, date=date_str)
        + f" — {total_str}"
    )


def _format_profile_view(user, graves: list, orders: list, lang: str) -> str:
    """Format profile view with user info, graves list, and order history."""
    lang_label = LANG_NAMES.get(user.language, user.language)
    text = get_text(
        lang,
        "my_profile",
        full_name=user.full_name or "—",
        phone_number=user.phone_number or "—",
        language=lang_label,
    )
    text += "\n\n"
    if graves:
        text += get_text(lang, "profile_graves_title") + "\n"
        for i, g in enumerate(graves, 1):
            birth = format_grave_date(
                g.birth_year, getattr(g, "birth_month", None),
                getattr(g, "birth_approximate", False), lang
            )
            death = format_grave_date(
                g.death_year, getattr(g, "death_month", None),
                getattr(g, "death_approximate", False), lang
            )
            text += get_text(
                lang,
                "profile_grave_item",
                num=i,
                name=g.deceased_full_name,
                relationship=g.relationship_status,
                cemetery=g.cemetery or "—",
                birth=birth,
                death=death,
            ) + "\n\n"
    else:
        text += get_text(lang, "profile_graves_empty")
    text += "\n"
    text += get_text(lang, "order_history_title") + "\n"
    if orders:
        for o in orders[:10]:
            text += _format_order_list_item(o, lang) + "\n"
        if len(orders) > 10:
            text += get_text(lang, "order_history_more", count=len(orders) - 10) + "\n"
    else:
        text += get_text(lang, "order_history_empty")
    return text


# -----------------------------------------------------------------------------
# Profile view (main menu button)
# -----------------------------------------------------------------------------


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_profile"),
            get_text("ru", "btn_profile"),
            get_text("uz", "btn_profile"),
        ]
    )
)
async def show_profile_menu(message: Message, state: FSMContext) -> None:
    """Show profile view or prompt to complete profile."""
    telegram_id = message.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
    lang = await _get_lang(telegram_id)
    if not user or not user.full_name or not user.phone_number:
        await state.set_state(ProfileState.full_name)
        await message.answer(get_text(lang, "enter_full_name"))
        return
    async with async_session_factory() as session:
        graves = await list_user_graves(session, user.id)
        orders = await get_orders_by_user(session, user.id)
    text = _format_profile_view(user, graves, orders, lang)
    kb = profile_inline(lang)
    if orders:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        order_buttons = [
            [InlineKeyboardButton(
                text=f"#{o.id} — {get_status_label(lang, o.status)}",
                callback_data=f"order:detail:{o.id}",
            )]
            for o in orders[:10]
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=kb.inline_keyboard + order_buttons)
    await message.answer(
        text,
        reply_markup=kb,
    )
    await message.answer(
        get_text(lang, "main_menu"),
        reply_markup=profile_menu_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# Main menu (from profile menu)
# -----------------------------------------------------------------------------


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_main_menu"),
            get_text("ru", "btn_main_menu"),
            get_text("uz", "btn_main_menu"),
        ]
    )
)
async def back_to_main_menu(message: Message) -> None:
    """Return to main menu — greet user by name."""
    telegram_id = message.from_user.id
    lang = await _get_lang(telegram_id)
    # Ismi bilan murojat
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
    name = (user.full_name if user else None) or message.from_user.first_name or ""
    await message.answer(
        get_text(lang, "welcome_back", name=name),
        reply_markup=main_menu_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# Profile update (inline button)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data == "profile:language")
async def change_language(callback: CallbackQuery) -> None:
    """Show language selection buttons (inline callback)."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    await callback.message.edit_text(
        get_text(lang, "choose_language"),
        reply_markup=language_inline(),
    )


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_change_language"),
            get_text("ru", "btn_change_language"),
            get_text("uz", "btn_change_language"),
        ]
    )
)
async def change_language_reply(message: Message) -> None:
    """Show language selection buttons (reply button)."""
    lang = await _get_lang(message.from_user.id)
    await message.answer(
        get_text(lang, "choose_language"),
        reply_markup=language_inline(),
    )


@router.callback_query(lambda c: c.data == "profile:update")
async def start_profile_update(callback: CallbackQuery, state: FSMContext) -> None:
    """Start profile update flow: ask for full name."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    await state.set_state(ProfileState.full_name)
    await callback.message.answer(get_text(lang, "enter_full_name"))


@router.message(ProfileState.full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    """Validate full name, save to bot DB + Django, ask for phone."""
    if not is_valid_full_name(message.text or ""):
        lang = await _get_lang(message.from_user.id)
        await message.answer(get_text(lang, "invalid_name"))
        return
    full_name = (message.text or "").strip()
    telegram_id = message.from_user.id
    username = message.from_user.username or ""

    # Bot DB
    async with async_session_factory() as session:
        await create_or_update_user(session, telegram_id, full_name=full_name)
        await session.commit()

    # Django DB
    await save_user_profile(telegram_id, full_name=full_name, username=username)

    lang = await _get_lang(telegram_id)
    await state.set_state(ProfileState.phone)
    await message.answer(
        get_text(lang, "enter_phone"),
        reply_markup=phone_keyboard(lang),
    )


@router.message(ProfileState.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    """Process phone from shared Telegram contact."""
    contact = message.contact
    if not contact or not contact.phone_number:
        return
    phone = (contact.phone_number or "").strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone_and_finish(message, state, phone)


@router.message(ProfileState.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    """Process phone from typed text."""
    phone = (message.text or "").strip()
    if not is_valid_phone(phone):
        lang = await _get_lang(message.from_user.id)
        await message.answer(get_text(lang, "invalid_phone"))
        return
    phone = normalize_phone(phone)
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone_and_finish(message, state, phone)


async def _save_phone_and_finish(
    message: Message, state: FSMContext, phone: str
) -> None:
    """Save phone, sync to Django + Google Sheets, clear state, show profile menu."""
    telegram_id = message.from_user.id
    username = message.from_user.username or ""

    # Bot DB
    async with async_session_factory() as session:
        await create_or_update_user(session, telegram_id, phone_number=phone)
        await session.commit()
        user = await get_user_by_telegram_id(session, telegram_id)
        full_name = user.full_name if user else ""

    lang = await _get_lang(telegram_id)

    # Django DB (admin panel)
    await save_user_profile(
        telegram_id,
        full_name=full_name,
        phone_number=phone,
        username=username,
    )

    # Google Sheets sync
    if SPREADSHEET_ID and GOOGLE_CREDENTIALS_PATH:
        await sync_user_to_sheet(
            SPREADSHEET_ID,
            GOOGLE_CREDENTIALS_PATH,
            telegram_id=telegram_id,
            full_name=full_name,
            phone_number=phone,
            username=username,
            language=lang,
        )

    await state.clear()
    await message.answer(
        get_text(lang, "profile_saved"),
        reply_markup=profile_menu_keyboard(lang),
    )

"""
Start command, language selection, registration (name + phone), Add Grave flow, main menu.
"""
from typing import Optional

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from apps.botapp.helpers import get_user_language, save_user_language, save_user_profile, user_exists
from bot.database.analytics import (
    track_event,
    EVENT_START,
    EVENT_LANGUAGE_SELECT,
    EVENT_REGISTRATION_NAME,
    EVENT_REGISTRATION_COMPLETE,
)
from bot.database.db import async_session_factory
from bot.database.queries import (
    create_or_update_user,
    get_regions,
    get_user_by_telegram_id,
    list_user_graves,
)
from bot.keyboards.inline import grave_regions_inline, language_inline
from bot.keyboards.reply import main_menu_keyboard, phone_keyboard
from bot.services.google_sheets import sync_user_to_sheet
from bot.states.forms import GraveState, RegistrationState
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_full_name, is_valid_phone, normalize_phone
from bot_config import GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID

router = Router(name="start")


def _is_registered(user) -> bool:
    """Check if user has completed registration (name only)."""
    return user and user.full_name


async def _get_lang(telegram_id: int) -> str:
    """Get user language from Django DB."""
    return await get_user_language(telegram_id)


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: Optional[FSMContext] = None
) -> None:
    """
    Handle /start.
    New user: language selection -> registration -> Add Grave.
    Existing user: saved language -> check registration -> main menu / Add Grave.
    """
    if state:
        await state.clear()
    telegram_id = message.from_user.id

    # Track /start event
    await track_event(telegram_id, EVENT_START)

    exists = await user_exists(telegram_id)

    if not exists:
        await save_user_language(telegram_id, "uz")
        async with async_session_factory() as session:
            await create_or_update_user(session, telegram_id, language="uz")
            await session.commit()
        await message.answer(
            get_text("uz", "choose_language"),
            reply_markup=language_inline(),
        )
        return

    lang = await get_user_language(telegram_id)

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if _is_registered(user):
            await create_or_update_user(session, telegram_id)
            await session.commit()
            graves = await list_user_graves(session, user.id)
            if graves:
                # Ismi bilan salomlashish
                name = user.full_name or message.from_user.first_name or ""
                await message.answer(
                    get_text(lang, "welcome_back", name=name),
                    reply_markup=main_menu_keyboard(lang),
                )
                return
            await _start_add_grave_flow(message, state, lang)
            return
        if not user:
            await create_or_update_user(session, telegram_id, language=lang)
            await session.commit()
    await state.set_state(RegistrationState.full_name)
    await message.answer(get_text(lang, "registration_required"))


async def _start_add_grave_flow(message: Message, state: FSMContext, lang: str) -> None:
    """Start Add Grave flow: region -> district -> cemetery -> deceased -> relationship."""
    async with async_session_factory() as session:
        regions = await get_regions(session)
    await state.set_state(GraveState.region)
    await state.update_data(lang=lang)
    await message.answer(get_text(lang, "welcome_short"))
    await message.answer(
        get_text(lang, "grave_enter_region"),
        reply_markup=grave_regions_inline(regions, lang),
    )


# -----------------------------------------------------------------------------
# Registration flow: full_name -> phone
# -----------------------------------------------------------------------------


@router.message(RegistrationState.full_name, lambda m: m.text)
async def process_registration_name(message: Message, state: FSMContext) -> None:
    """Validate full name, save, and complete registration."""
    if not is_valid_full_name(message.text or ""):
        lang = await _get_lang(message.from_user.id)
        await message.answer(get_text(lang, "invalid_name"))
        return
    full_name = (message.text or "").strip()
    telegram_id = message.from_user.id
    username = message.from_user.username or ""
    lang = await _get_lang(telegram_id)

    # Track name entry
    await track_event(telegram_id, EVENT_REGISTRATION_NAME)

    # Save to bot SQLAlchemy DB
    async with async_session_factory() as session:
        await create_or_update_user(session, telegram_id, full_name=full_name)
        await session.commit()

    from bot.middlewares.registration import invalidate_reg_cache
    invalidate_reg_cache(telegram_id)

    # Track registration complete
    await track_event(telegram_id, EVENT_REGISTRATION_COMPLETE)

    # Save to Django DB
    await save_user_profile(
        telegram_id,
        full_name=full_name,
        username=username,
        language=lang,
    )

    # Sync to Google Sheets
    if SPREADSHEET_ID and GOOGLE_CREDENTIALS_PATH:
        await sync_user_to_sheet(
            SPREADSHEET_ID,
            GOOGLE_CREDENTIALS_PATH,
            telegram_id=telegram_id,
            full_name=full_name,
            phone_number="",
            username=username,
            language=lang,
        )

    await state.clear()
    await message.answer(get_text(lang, "registration_complete", name=full_name))
    await _start_add_grave_flow(message, state, lang)


@router.message(RegistrationState.phone, lambda m: m.contact)
async def process_registration_phone_contact(message: Message, state: FSMContext) -> None:
    """Process phone from shared Telegram contact."""
    contact = message.contact
    if not contact or not contact.phone_number:
        return
    phone = (contact.phone_number or "").strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    await _finish_registration(message, state, phone)


@router.message(RegistrationState.phone, lambda m: m.text)
async def process_registration_phone_text(message: Message, state: FSMContext) -> None:
    """Process phone from typed text."""
    phone = (message.text or "").strip()
    if not is_valid_phone(phone):
        lang = await _get_lang(message.from_user.id)
        await message.answer(get_text(lang, "invalid_phone"))
        return
    phone = normalize_phone(phone)
    if not phone.startswith("+"):
        phone = "+" + phone
    await _finish_registration(message, state, phone)


async def _finish_registration(message: Message, state: FSMContext, phone: str) -> None:
    """Save phone to DB + Django + Google Sheets, then start Add Grave flow."""
    telegram_id = message.from_user.id
    username = message.from_user.username or ""
    data = await state.get_data()
    full_name = data.get("reg_full_name", "")
    if not full_name:
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            full_name = user.full_name if user else ""

    # 1. Save to bot SQLAlchemy DB
    async with async_session_factory() as session:
        await create_or_update_user(session, telegram_id, phone_number=phone)
        await session.commit()

    from bot.middlewares.registration import invalidate_reg_cache
    invalidate_reg_cache(telegram_id)

    lang = await _get_lang(telegram_id)

    # 2. Save to Django DB (admin panel — single source of truth)
    await save_user_profile(
        telegram_id,
        full_name=full_name,
        phone_number=phone,
        username=username,
        language=lang,
    )

    # 3. Sync to Google Sheets (mirror/copy)
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
    await message.answer(get_text(lang, "registration_complete"))
    await _start_add_grave_flow(message, state, lang)


# -----------------------------------------------------------------------------
# Language selection (callback from initial prompt or profile change)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def callback_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Save language selection, then proceed to registration or main menu."""
    lang = callback.data.split(":")[1]
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    await callback.answer()
    telegram_id = callback.from_user.id

    await save_user_language(telegram_id, lang)

    # Track language selection
    await track_event(telegram_id, EVENT_LANGUAGE_SELECT, {"language": lang})

    async with async_session_factory() as session:
        await create_or_update_user(session, telegram_id, language=lang)
        await session.commit()
        user = await get_user_by_telegram_id(session, telegram_id)

        if _is_registered(user):
            graves = await list_user_graves(session, user.id)
            await callback.message.edit_text(get_text(lang, "language_selected"))
            if graves:
                name = user.full_name or callback.from_user.first_name or ""
                await callback.message.answer(
                    get_text(lang, "welcome_back", name=name),
                    reply_markup=main_menu_keyboard(lang),
                )
                return
            await _start_add_grave_flow(callback.message, state, lang)
            return

    await callback.message.edit_text(get_text(lang, "language_selected"))
    await state.set_state(RegistrationState.full_name)
    await callback.message.answer(get_text(lang, "registration_required"))

"""
Start command, language selection, and mandatory registration.

Registration is asked ONCE for a new user, in this order:
    language  ->  phone (contact)  ->  full name  ->  main menu

All user data is saved in ONE place — the `users` table (bot.database).
The same record is used by the website, so the bot and the site share data.
"""
from typing import Optional

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from apps.botapp.helpers import get_user_language, save_user_language
from bot.database.analytics import (
    track_event,
    EVENT_START,
    EVENT_LANGUAGE_SELECT,
    EVENT_REGISTRATION_NAME,
    EVENT_REGISTRATION_COMPLETE,
)
from bot.database.db import async_session_factory
from bot.database.queries import create_or_update_user, get_user_by_telegram_id
from bot.keyboards.inline import language_inline
from bot.keyboards.reply import main_menu_keyboard, phone_keyboard
from bot.middlewares.registration import invalidate_reg_cache
from bot.services.google_sheets import sync_user_to_sheet
from bot.states.forms import RegistrationState
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_full_name, is_valid_phone, normalize_phone
from bot_config import GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID

router = Router(name="start")


def _is_registered(user) -> bool:
    """Foydalanuvchi to'liq ro'yxatdan o'tganmi — ism VA telefon bo'lishi shart."""
    return bool(user and user.full_name and user.phone_number)


async def _get_lang(telegram_id: int) -> str:
    return await get_user_language(telegram_id)


@router.message(CommandStart())
async def cmd_start(message: Message, state: Optional[FSMContext] = None) -> None:
    """/start — ro'yxatdan o'tgan bo'lsa asosiy menyu, bo'lmasa til tanlash."""
    if state:
        await state.clear()
    telegram_id = message.from_user.id
    await track_event(telegram_id, EVENT_START)

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if user is None:
            user = await create_or_update_user(session, telegram_id, language="uz")
            await session.commit()

    if _is_registered(user):
        lang = user.language or "uz"
        name = user.full_name or message.from_user.first_name or ""
        await message.answer(
            get_text(lang, "welcome_back", name=name),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    # Yangi (yoki to'liq ro'yxatdan o'tmagan) foydalanuvchi — til tanlashdan boshlaymiz
    await message.answer(get_text("uz", "choose_language"), reply_markup=language_inline())


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def callback_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Til tanlandi -> ro'yxatdan o'tgan bo'lsa menyu, bo'lmasa telefon so'raladi."""
    lang = callback.data.split(":")[1]
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    await callback.answer()
    telegram_id = callback.from_user.id

    await track_event(telegram_id, EVENT_LANGUAGE_SELECT, {"language": lang})
    await save_user_language(telegram_id, lang)

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)

    await callback.message.edit_text(get_text(lang, "language_selected"))

    if _is_registered(user):
        name = user.full_name or callback.from_user.first_name or ""
        await callback.message.answer(
            get_text(lang, "welcome_back", name=name),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    # Ro'yxatdan o'tish — 1-qadam: telefon raqami
    await state.set_state(RegistrationState.phone)
    await callback.message.answer(
        get_text(lang, "registration_phone"),
        reply_markup=phone_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# Registration: phone -> full name (asked once)
# -----------------------------------------------------------------------------


@router.message(RegistrationState.phone, lambda m: m.contact)
async def registration_phone_contact(message: Message, state: FSMContext) -> None:
    """Telefon — ulashilgan Telegram kontaktidan."""
    contact = message.contact
    if not contact or not contact.phone_number:
        return
    phone = (contact.phone_number or "").strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone_ask_name(message, state, phone)


@router.message(RegistrationState.phone, lambda m: m.text)
async def registration_phone_text(message: Message, state: FSMContext) -> None:
    """Telefon — qo'lda yozilgan matndan."""
    phone = (message.text or "").strip()
    if not is_valid_phone(phone):
        lang = await _get_lang(message.from_user.id)
        await message.answer(get_text(lang, "invalid_phone"))
        return
    phone = normalize_phone(phone)
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone_ask_name(message, state, phone)


async def _save_phone_ask_name(message: Message, state: FSMContext, phone: str) -> None:
    """Telefonni saqlaydi, keyin ismni so'raydi."""
    telegram_id = message.from_user.id
    async with async_session_factory() as session:
        await create_or_update_user(session, telegram_id, phone_number=phone)
        await session.commit()
    lang = await _get_lang(telegram_id)
    await state.set_state(RegistrationState.full_name)
    await message.answer(get_text(lang, "registration_required"))


@router.message(RegistrationState.full_name, lambda m: m.text)
async def registration_name(message: Message, state: FSMContext) -> None:
    """Ism — validatsiya qilib saqlaydi va ro'yxatdan o'tishni yakunlaydi."""
    lang = await _get_lang(message.from_user.id)
    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return
    full_name = (message.text or "").strip()
    telegram_id = message.from_user.id

    await track_event(telegram_id, EVENT_REGISTRATION_NAME)

    async with async_session_factory() as session:
        user = await create_or_update_user(session, telegram_id, full_name=full_name)
        await session.commit()
        phone = user.phone_number

    invalidate_reg_cache(telegram_id)
    await track_event(telegram_id, EVENT_REGISTRATION_COMPLETE)

    # Google Sheets — bu faqat nusxa (asosiy manba `users` jadvali)
    if SPREADSHEET_ID and GOOGLE_CREDENTIALS_PATH:
        try:
            await sync_user_to_sheet(
                SPREADSHEET_ID, GOOGLE_CREDENTIALS_PATH,
                telegram_id=telegram_id,
                full_name=full_name,
                phone_number=phone,
                username=message.from_user.username or "",
                language=lang,
            )
        except Exception:  # noqa: BLE001 — Sheets ishlamasa ham ro'yxatdan o'tish davom etsin
            pass

    await state.clear()
    await message.answer(
        get_text(lang, "registration_complete", name=full_name),
        reply_markup=main_menu_keyboard(lang),
    )

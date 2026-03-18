"""
Complaints and suggestions. User sends message, bot forwards to admins.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.db import async_session_factory
from bot.database.queries import create_complaint, get_user_by_telegram_id
from bot.keyboards.reply import cancel_keyboard, main_menu_keyboard
from bot.services.notifications import forward_complaint_to_admins
from bot.states.forms import ComplaintState
from bot.utils.texts import get_text

router = Router(name="complaints")


async def _get_lang(telegram_id: int) -> str:
    """Get user language from DB."""
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


def _is_cancel(text: str) -> bool:
    """Check if user pressed cancel."""
    return text.strip() in [
        get_text("en", "btn_cancel"),
        get_text("ru", "btn_cancel"),
        get_text("uz", "btn_cancel"),
    ]


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_complaints"),
            get_text("ru", "btn_complaints"),
            get_text("uz", "btn_complaints"),
        ]
    )
)
async def start_complaint(message: Message, state: FSMContext) -> None:
    """Start complaint flow: ask for text."""
    lang = await _get_lang(message.from_user.id)
    await state.set_state(ComplaintState.waiting_for_text)
    await message.answer(
        get_text(lang, "complaints_prompt"),
        reply_markup=cancel_keyboard(lang),
    )


@router.message(ComplaintState.waiting_for_text, F.text)
async def process_complaint_text(message: Message, state: FSMContext) -> None:
    """Process complaint text: forward to admins, save to DB, finish."""
    if _is_cancel(message.text or ""):
        lang = await _get_lang(message.from_user.id)
        await state.clear()
        await message.answer(
            get_text(lang, "complaints_cancel"),
            reply_markup=main_menu_keyboard(lang),
        )
        return
    text = (message.text or "").strip()
    if not text:
        return
    telegram_id = message.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if user:
            await create_complaint(session, user.id, text)
            await session.commit()
            user_name = user.full_name or "Unknown"
            user_phone = user.phone_number or "—"
        else:
            user_name = message.from_user.full_name or "Unknown"
            user_phone = "—"
    # Forward to admins (user info: telegram ID, full name, phone)
    await forward_complaint_to_admins(
        message.bot,
        user_id=telegram_id,
        user_name=user_name,
        user_phone=user_phone,
        text=text,
    )
    lang = await _get_lang(telegram_id)
    await state.clear()
    await message.answer(
        get_text(lang, "complaints_sent"),
        reply_markup=main_menu_keyboard(lang),
    )

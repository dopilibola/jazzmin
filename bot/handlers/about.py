"""
About Us: static information about the company/service.
Content is structured in about_content.py for easy migration to DB/admin panel later.
"""
from aiogram import F, Router
from aiogram.types import Message

from bot.database.db import async_session_factory
from bot.database.queries import get_user_by_telegram_id
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.about_content import get_about_content
from bot.utils.texts import get_text

router = Router(name="about")


async def _get_lang(telegram_id: int) -> str:
    """Get user language from DB."""
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_about"),
            get_text("ru", "btn_about"),
            get_text("uz", "btn_about"),
        ]
    )
)
async def show_about(message: Message) -> None:
    """Show about us content (from about_content module; can be moved to DB later)."""
    lang = await _get_lang(message.from_user.id)
    content = get_about_content(lang)
    await message.answer(
        content,
        reply_markup=main_menu_keyboard(lang),
    )

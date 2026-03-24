"""
About Us: static information about the company/service.
Content is structured in about_content.py for easy migration to DB/admin panel later.
"""
from aiogram import F, Router
from aiogram.types import Message

from apps.botapp.helpers import get_user_language as _get_lang
from bot.keyboards.reply import back_to_main_keyboard
from bot.utils.about_content import get_about_content
from bot.utils.texts import get_text

router = Router(name="about")


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
    """Show about us content with back button."""
    lang = await _get_lang(message.from_user.id)
    content = get_about_content(lang)
    await message.answer(
        content,
        reply_markup=back_to_main_keyboard(lang),
    )

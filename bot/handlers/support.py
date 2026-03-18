"""
Support: redirect user to support link (from env SUPPORT_LINK).
"""
from aiogram import F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from apps.botapp.helpers import get_user_language as _get_lang
from bot.utils.texts import get_text

from bot_config import SUPPORT_LINK

router = Router(name="support")


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_support"),
            get_text("ru", "btn_support"),
            get_text("uz", "btn_support"),
        ]
    )
)
async def show_support_link(message: Message) -> None:
    """Show support link - user clicks to open (redirect to link from env)."""
    lang = await _get_lang(message.from_user.id)
    if SUPPORT_LINK:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=get_text(lang, "btn_support"), url=SUPPORT_LINK)],
            ]
        )
        await message.answer(get_text(lang, "support_link_message"), reply_markup=kb)
    else:
        await message.answer(get_text(lang, "support_link_not_configured"))

"""
Subscription plans: monthly plans, cleanings per month, photo report.
Simple informational screen.
"""
from aiogram import F, Router
from aiogram.types import Message

from apps.botapp.helpers import get_user_language as _get_lang
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.texts import get_text

router = Router(name="subscriptions")


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_subscriptions"),
            get_text("ru", "btn_subscriptions"),
            get_text("uz", "btn_subscriptions"),
        ]
    )
)
async def show_subscriptions(message: Message) -> None:
    """Show subscription plans info."""
    lang = await _get_lang(message.from_user.id)
    await message.answer(
        get_text(lang, "subscriptions_info"),
        reply_markup=main_menu_keyboard(lang),
    )

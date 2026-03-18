"""
Subscription plans: monthly plans, cleanings per month, photo report.
Simple informational screen.
"""
from aiogram import F, Router
from aiogram.types import Message

from bot.database.db import async_session_factory
from bot.database.queries import get_user_by_telegram_id
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.texts import get_text

router = Router(name="subscriptions")


async def _get_lang(telegram_id: int) -> str:
    """Get user language from DB."""
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


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

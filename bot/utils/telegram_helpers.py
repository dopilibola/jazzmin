"""
Telegram API helpers (e.g. safe edit to avoid "message is not modified" errors).
"""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery


async def safe_edit_text(
    callback: CallbackQuery, text: str, reply_markup=None
) -> None:
    """
    Edit message text, ignoring Telegram's "message is not modified" error.
    This occurs when the new content is identical to the current content.
    """
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

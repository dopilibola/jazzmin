"""
Middleware: block unregistered users from using the bot.
Only /start and registration flow are allowed for unregistered users.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from bot.database.db import async_session_factory
from bot.database.queries import get_user_by_telegram_id
from bot.states.forms import RegistrationState
from bot.utils.texts import get_text


def _is_registered(user) -> bool:
    return user and user.full_name and user.phone_number


def _get_event_and_user(update: Update) -> tuple[Message | CallbackQuery | None, int | None, int | None]:
    """Extract event, user_id, chat_id from Update."""
    ev = update.message or update.callback_query or update.edited_message
    if not ev:
        return None, None, None
    user = getattr(ev, "from_user", None)
    chat = getattr(ev, "chat", None)
    if not user or not chat:
        return ev, None, None
    return ev, user.id, chat.id


def _is_start_or_lang(update: Update) -> bool:
    """Allow /start command or lang: callback without DB check."""
    if update.message and (update.message.text or "").strip() == "/start":
        return True
    if update.callback_query and update.callback_query.data and update.callback_query.data.startswith("lang:"):
        return True
    return False


class RegistrationMiddleware(BaseMiddleware):
    """
    Block unregistered users. Allow: /start, lang: callback, and RegistrationState.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Outer middleware receives Update
        update = event if isinstance(event, Update) else None
        if not update:
            return await handler(event, data)

        if _is_start_or_lang(update):
            return await handler(event, data)

        ev, user_id, chat_id = _get_event_and_user(update)
        if not ev or user_id is None or chat_id is None:
            return await handler(event, data)

        # Check FSM state - if in registration, allow
        bot = data.get("bot")
        dp = data.get("dispatcher")
        if bot and dp and dp.storage:
            from aiogram.fsm.context import FSMContext
            from aiogram.fsm.storage.base import StorageKey
            key = StorageKey(bot_id=bot.id, chat_id=chat_id, user_id=user_id)
            fsm = FSMContext(storage=dp.storage, key=key)
            current = await fsm.get_state()
            if current and RegistrationState.__name__ in (current or ""):
                return await handler(event, data)

        # Check if user is registered in DB
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, user_id)
            if _is_registered(user):
                return await handler(event, data)

        # Not registered - block and prompt
        lang = user.language if user else "ru"
        msg = get_text(lang, "registration_required")
        if isinstance(ev, Message):
            await ev.answer(msg)
        elif isinstance(ev, CallbackQuery):
            await ev.answer(msg, show_alert=True)
        return None  # Don't call handler - block

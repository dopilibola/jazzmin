"""
Middleware: block unregistered users from using the bot.
Only /start and registration flow are allowed for unregistered users.

Performance: caches registration status per user for 120 s to avoid
hitting the DB on every single update.
"""
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from bot.database.db import async_session_factory
from bot.database.queries import get_user_by_telegram_id
from bot.states.forms import RegistrationState
from bot.utils.texts import get_text

_reg_cache: dict[int, tuple[float, bool]] = {}
_REG_TTL = 120.0


def _is_registered(user) -> bool:
    return user and user.full_name and user.phone_number


def _check_reg_cache(user_id: int) -> bool | None:
    entry = _reg_cache.get(user_id)
    if entry and (time.monotonic() - entry[0]) < _REG_TTL:
        return entry[1]
    return None


def _set_reg_cache(user_id: int, registered: bool) -> None:
    _reg_cache[user_id] = (time.monotonic(), registered)


def invalidate_reg_cache(user_id: int) -> None:
    """Call after registration completes to force next check from DB."""
    _reg_cache.pop(user_id, None)


def _get_event_and_user(update: Update) -> tuple[Message | CallbackQuery | None, int | None, int | None]:
    ev = update.message or update.callback_query or update.edited_message
    if not ev:
        return None, None, None
    user = getattr(ev, "from_user", None)
    chat = getattr(ev, "chat", None)
    if not user or not chat:
        return ev, None, None
    return ev, user.id, chat.id


def _is_start_or_lang(update: Update) -> bool:
    if update.message and (update.message.text or "").strip() == "/start":
        return True
    if update.callback_query and update.callback_query.data and update.callback_query.data.startswith("lang:"):
        return True
    return False


class RegistrationMiddleware(BaseMiddleware):
    """Block unregistered users. Allow: /start, lang: callback, and RegistrationState."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update = event if isinstance(event, Update) else None
        if not update:
            return await handler(event, data)

        if _is_start_or_lang(update):
            return await handler(event, data)

        ev, user_id, chat_id = _get_event_and_user(update)
        if not ev or user_id is None or chat_id is None:
            return await handler(event, data)

        # Fast path: check in-memory cache first
        cached = _check_reg_cache(user_id)
        if cached is True:
            return await handler(event, data)

        # Check FSM state — if in registration, allow
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

        # DB check (only if cache miss)
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, user_id)
            if _is_registered(user):
                _set_reg_cache(user_id, True)
                return await handler(event, data)

        lang = data.get("lang") or (user.language if user else "uz")
        msg = get_text(lang, "registration_required")
        if isinstance(ev, Message):
            await ev.answer(msg)
        elif isinstance(ev, CallbackQuery):
            await ev.answer(msg, show_alert=True)
        return None

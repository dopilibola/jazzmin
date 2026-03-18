"""
Middleware: auto-detect user language on every incoming update.
Injects ``data["lang"]`` so any handler can access it.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update


class LanguageMiddleware(BaseMiddleware):
    """Set data['lang'] from Django DB on every update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update = event if isinstance(event, Update) else None
        if not update:
            return await handler(event, data)

        ev = update.message or update.callback_query or update.edited_message
        if ev:
            from_user = getattr(ev, "from_user", None)
            if from_user:
                from apps.botapp.helpers import get_user_language

                data["lang"] = await get_user_language(from_user.id)

        return await handler(event, data)

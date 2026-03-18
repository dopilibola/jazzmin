"""
Middleware: automatic retry on TelegramNetworkError.
Retries the handler up to MAX_RETRIES times with exponential backoff
when the Telegram API request times out due to slow network.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
BASE_DELAY = 3.0


class RetryMiddleware(BaseMiddleware):
    """Retry handler execution on TelegramNetworkError."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                return await handler(event, data)
            except TelegramNetworkError as exc:
                last_exc = exc
                if attempt <= MAX_RETRIES:
                    delay = BASE_DELAY * attempt
                    logger.warning(
                        "TelegramNetworkError (attempt %d/%d), retrying in %.1fs: %s",
                        attempt,
                        MAX_RETRIES + 1,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "TelegramNetworkError after %d attempts, giving up: %s",
                        attempt,
                        exc,
                    )
        raise last_exc

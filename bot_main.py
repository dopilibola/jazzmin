"""
Main entry point. Grave Care Service Telegram Bot.
Integrated into the Django project — shares the same PostgreSQL database.
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bassic.settings")

import django  # noqa: E402
django.setup()

import asyncio  # noqa: E402
import logging  # noqa: E402

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from bot.database.db import close_db, init_db  # noqa: E402
from bot.middlewares.language import LanguageMiddleware  # noqa: E402
from bot.middlewares.registration import RegistrationMiddleware  # noqa: E402
from bot.middlewares.retry import RetryMiddleware  # noqa: E402
from bot.handlers import (  # noqa: E402
    about,
    cart,
    checkout,
    flowers,
    graves,
    orders,
    payment,
    profile,
    services,
    start,
    support,
)
from bot_config import BOT_TOKEN  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """Initialize database and seed data."""
    await init_db()
    logger.info("Database initialized.")


def _patch_telegram_dns():
    """Route api.telegram.org to a reachable datacenter IP.

    The default DNS result (149.154.166.110) is blocked by some ISPs.
    This patches socket.getaddrinfo to resolve api.telegram.org to a
    working Telegram datacenter IP instead.
    """
    import socket

    _WORKING_IP = "149.154.167.220"
    _original = socket.getaddrinfo

    def _patched(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.telegram.org":
            return _original(_WORKING_IP, port, family, type, proto, flags)
        return _original(host, port, family, type, proto, flags)

    socket.getaddrinfo = _patched
    logger.info("DNS override: api.telegram.org -> %s", _WORKING_IP)


async def main() -> None:
    """Run the bot."""
    import socket

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Check your .env file.")
        return

    _patch_telegram_dns()

    from aiogram.client.session.aiohttp import AiohttpSession
    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    session.timeout = 300

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(RetryMiddleware())
    dp.update.outer_middleware(LanguageMiddleware())
    dp.update.outer_middleware(RegistrationMiddleware())
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(graves.router)
    dp.include_router(services.router)
    dp.include_router(flowers.router)
    dp.include_router(cart.router)
    dp.include_router(checkout.router)
    dp.include_router(payment.router)
    dp.include_router(orders.router)
    dp.include_router(support.router)
    dp.include_router(about.router)
    dp.startup.register(on_startup)
    dp.shutdown.register(close_db)

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Starting bot (attempt %d/%d)...", attempt, max_retries)
            await dp.start_polling(bot)
            break
        except Exception as exc:
            logger.error("Bot startup failed (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                wait = 10 * attempt
                logger.info("Retrying in %d seconds...", wait)
                await asyncio.sleep(wait)
            else:
                logger.error("All %d startup attempts failed. Exiting.", max_retries)
                await bot.session.close()
                raise


if __name__ == "__main__":
    asyncio.run(main())

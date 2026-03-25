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
from bot.middlewares.analytics import AnalyticsMiddleware, StateTrackingMiddleware  # noqa: E402
from bot.middlewares.language import LanguageMiddleware  # noqa: E402
from bot.middlewares.registration import RegistrationMiddleware, clear_all_reg_cache  # noqa: E402
from bot.middlewares.retry import RetryMiddleware  # noqa: E402
from bot.handlers import (  # noqa: E402
    about,
    analytics,
    cart,
    checkout,
    complaint,
    # flowers,  # COMMENTED OUT
    graves,
    orders,
    payment,
    profile,
    services,
    start,
    submission,
    support,
)
from bot.handlers.payment_verification import run_verification_bot  # noqa: E402
from bot.handlers.order_workflow import router as order_workflow_router, start_reminder_task  # noqa: E402
from bot_config import BOT_TOKEN, PAYMENT_BOT_TOKEN  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


_main_bot_instance = None


async def on_startup() -> None:
    """Initialize database, seed data, and start reminder task."""
    await init_db()
    logger.info("Database initialized.")
    # Clear registration cache on startup
    clear_all_reg_cache()
    logger.info("Registration cache cleared.")
    # Start reminder task after DB is ready
    if _main_bot_instance:
        start_reminder_task(_main_bot_instance)
        logger.info("Order reminder task started.")


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
    global _main_bot_instance
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

    # Set global bot instance for reminder task
    _main_bot_instance = bot

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(AnalyticsMiddleware())  # Analytics first - tracks everything
    dp.update.outer_middleware(StateTrackingMiddleware())  # Track state transitions
    dp.update.outer_middleware(RetryMiddleware())
    dp.update.outer_middleware(LanguageMiddleware())
    dp.update.outer_middleware(RegistrationMiddleware())
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(graves.router)
    dp.include_router(services.router)
    # dp.include_router(flowers.router)  # COMMENTED OUT
    dp.include_router(cart.router)
    dp.include_router(checkout.router)
    dp.include_router(payment.router)
    dp.include_router(orders.router)
    dp.include_router(submission.router)
    dp.include_router(support.router)
    dp.include_router(about.router)
    dp.include_router(analytics.router)
    dp.include_router(complaint.router)
    dp.include_router(order_workflow_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(close_db)

    # Create tasks for both bots
    tasks = []

    # Main bot task
    async def run_main_bot():
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Starting main bot (attempt %d/%d)...", attempt, max_retries)
                await dp.start_polling(bot)
                break
            except Exception as exc:
                logger.error("Main bot startup failed (attempt %d/%d): %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    wait = 10 * attempt
                    logger.info("Retrying in %d seconds...", wait)
                    await asyncio.sleep(wait)
                else:
                    logger.error("All %d startup attempts failed. Exiting.", max_retries)
                    await bot.session.close()
                    raise

    tasks.append(run_main_bot())

    # Verification bot task (if configured)
    if PAYMENT_BOT_TOKEN:
        logger.info("Payment verification bot (BOT_TOKEN3) configured. Starting...")
        tasks.append(run_verification_bot())
    else:
        logger.warning("PAYMENT_BOT_TOKEN (BOT_TOKEN3) not set. Verification bot disabled.")

    # Run all bots concurrently
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

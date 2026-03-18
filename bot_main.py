"""
Main entry point. Grave Care Service Telegram Bot.
Integrated into the Django project — shares the same PostgreSQL database.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.database.db import close_db, init_db
from bot.middlewares.registration import RegistrationMiddleware
from bot.handlers import (
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
from bot_config import BOT_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """Initialize database and seed data."""
    await init_db()
    logger.info("Database initialized.")


async def main() -> None:
    """Run the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Check your .env file.")
        return
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
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
    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

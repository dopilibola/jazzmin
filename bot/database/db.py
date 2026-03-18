"""
Database session and initialization.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.database.migrations import run_migrations
from bot.database.models import Base
from bot.database.seed import (
    seed_flower_categories_and_products,
    seed_flowers,
    seed_locations,
    seed_services,
)
from bot_config import DATABASE_URL


# Create async engine (SQLite requires check_same_thread=False)
_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Session factory
async_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """Yield an async session for dependency injection."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables, run migrations, seed locations. Call on startup."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await run_migrations(_engine)
    async with async_session_factory() as session:
        await seed_locations(session)
        await seed_services(session)
        await seed_flowers(session)
        await seed_flower_categories_and_products(session)
        await session.commit()


async def close_db() -> None:
    """Dispose engine. Call on shutdown."""
    await _engine.dispose()

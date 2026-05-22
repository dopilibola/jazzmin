"""Veb-ilova uchun qo'shimcha DB yordamchilari — bot bilan bir xil `users` jadvali."""
from sqlalchemy import select, text

from bot.database.db import _engine, async_session_factory
from bot.database.models import Base, User
from webapp.security import normalize_phone


async def ensure_web_schema() -> None:
    """Bot jadvallari mavjudligini va veb uchun ustunlar borligini ta'minlaydi (idempotent)."""
    # Yetishmayotgan jadvallarni yaratadi (mavjudlariga tegmaydi, seed qilmaydi)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        await session.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")
        )
        # Veb-only foydalanuvchilarda telegram_id NULL bo'lishi mumkin
        await session.execute(
            text("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL")
        )
        await session.commit()


async def get_user_by_phone(session, phone: str) -> User | None:
    """Telefon raqami bo'yicha foydalanuvchini topadi (format farqiga chidamli)."""
    digits = normalize_phone(phone)
    if not digits:
        return None
    last9 = digits[-9:]
    result = await session.execute(
        select(User).where(User.phone_number.like(f"%{last9}")).order_by(User.id)
    )
    return result.scalars().first()


async def get_user_by_id(session, user_id: int) -> User | None:
    """Foydalanuvchini PK (users.id) bo'yicha topadi."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_profile(
    session,
    user: User,
    *,
    full_name: str | None = None,
    phone: str | None = None,
    language: str | None = None,
    password_hash: str | None = None,
) -> User:
    """Foydalanuvchi profilini yangilaydi."""
    if full_name is not None:
        user.full_name = full_name
    if phone is not None:
        user.phone_number = normalize_phone(phone)
    if language is not None:
        user.language = language
    if password_hash is not None:
        user.password_hash = password_hash
    await session.flush()
    await session.refresh(user)
    return user

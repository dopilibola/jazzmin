"""
Async helpers for the Telegram bot.

User data (language, full name, phone) is stored in ONE place — the
SQLAlchemy `users` table (bot.database.models.User). The web app uses the
same table, so the bot and the website always share a single record per user.

Catalog (services/flowers) still uses Django ORM via sync_to_async.
"""
from __future__ import annotations

import logging
import time
from functools import partial

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

_to_async = partial(sync_to_async, thread_sensitive=False)


# ---------------------------------------------------------------------------
# Simple TTL cache (used only for per-user language)
# ---------------------------------------------------------------------------


class _TTLCache:
    """Minimal per-key TTL cache."""

    def __init__(self, ttl: float):
        self._ttl = ttl
        self._store: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        entry = self._store.get(key)
        if entry and (time.monotonic() - entry[0]) < self._ttl:
            return entry[1]
        return None

    def set(self, key: str, value: object) -> None:
        self._store[key] = (time.monotonic(), value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


_lang_cache = _TTLCache(ttl=120)


# ---------------------------------------------------------------------------
# User data — single source of truth: the `users` table (SQLAlchemy)
# ---------------------------------------------------------------------------


async def get_user_language(chat_id: int) -> str:
    """User tilini `users` jadvalidan oladi. 120 s keshlangan (har update'da chaqiriladi)."""
    key = str(chat_id)
    cached = _lang_cache.get(key)
    if cached is not None:
        return cached
    try:
        from bot.database.db import async_session_factory
        from bot.database.queries import get_user_by_telegram_id

        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, chat_id)
        lang = user.language if (user and user.language) else "uz"
    except Exception:  # noqa: BLE001 — middleware'da ishlaydi, hech qachon yiqilmasin
        logger.exception("get_user_language failed for %s", chat_id)
        lang = "uz"
    _lang_cache.set(key, lang)
    return lang


async def save_user_language(chat_id: int, language: str) -> None:
    """User tilini `users` jadvaliga saqlaydi va keshni yangilaydi."""
    from bot.database.db import async_session_factory
    from bot.database.queries import create_or_update_user

    async with async_session_factory() as session:
        await create_or_update_user(session, chat_id, language=language)
        await session.commit()
    _lang_cache.set(str(chat_id), language)


async def save_user_profile(
    chat_id: int,
    *,
    full_name: str | None = None,
    phone_number: str | None = None,
    username: str | None = None,  # `users` jadvalida username yo'q — e'tiborsiz qoldiriladi
    language: str | None = None,
) -> None:
    """User profilini `users` jadvaliga saqlaydi (faqat berilgan maydonlar)."""
    from bot.database.db import async_session_factory
    from bot.database.queries import create_or_update_user

    async with async_session_factory() as session:
        await create_or_update_user(
            session, chat_id,
            full_name=full_name,
            phone_number=phone_number,
            language=language,
        )
        await session.commit()
    if language is not None:
        _lang_cache.set(str(chat_id), language)


async def get_user_profile(chat_id: int) -> dict | None:
    """`users` jadvalidan to'liq profilni qaytaradi (dict) yoki None."""
    from bot.database.db import async_session_factory
    from bot.database.queries import get_user_by_telegram_id

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, chat_id)
    if not user:
        return None
    return {
        "chat_id": user.telegram_id,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "username": "",
        "language": user.language,
    }


async def user_exists(chat_id: int) -> bool:
    """`users` jadvalida shu chat_id uchun yozuv bor-yo'qligini tekshiradi."""
    from bot.database.db import async_session_factory
    from bot.database.queries import get_user_by_telegram_id

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, chat_id)
    return user is not None


# ---------------------------------------------------------------------------
# Catalog: Services — uses apps.catalog.models.Service (NO cache)
# ---------------------------------------------------------------------------


async def get_active_services() -> list:
    """Return all active services from Django DB. Always fresh."""

    @_to_async
    def _fetch():
        from apps.catalog.models import Service

        return list(Service.objects.filter(is_active=True).order_by("name"))

    return await _fetch()


async def get_service_by_pk(service_id: int):
    """Return a single service by primary key, or None."""

    @_to_async
    def _fetch():
        from apps.catalog.models import Service

        try:
            return Service.objects.get(pk=service_id)
        except Service.DoesNotExist:
            return None

    return await _fetch()


# ---------------------------------------------------------------------------
# Price helper
# ---------------------------------------------------------------------------


def format_price(price, lang: str = "en") -> str:
    """Format price (int, Decimal, or float) for display. Assumes UZS sum."""
    return f"{int(price):,} sum".replace(",", " ")

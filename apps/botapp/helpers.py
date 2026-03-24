"""
Async helpers for Telegram bot.
Uses Django ORM via sync_to_async for safe access from aiogram handlers.
Covers: user language, catalog services, flower categories/products.

Performance: user language is cached (middleware runs on every update).
Catalog queries have NO cache — they hit the DB every time so admin
changes appear instantly without restart.
"""
from __future__ import annotations

import time
from functools import partial

from asgiref.sync import sync_to_async

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
# User language (cached — runs on every update via middleware)
# ---------------------------------------------------------------------------


async def get_user_language(chat_id: int) -> str:
    """Fetch user language. Cached 120 s to avoid DB hit on every update."""
    key = str(chat_id)
    cached = _lang_cache.get(key)
    if cached is not None:
        return cached

    @_to_async
    def _fetch():
        from apps.botapp.models import TelegramUser

        try:
            return TelegramUser.objects.get(chat_id=chat_id).language
        except TelegramUser.DoesNotExist:
            return "uz"

    lang = await _fetch()
    _lang_cache.set(key, lang)
    return lang


async def save_user_language(chat_id: int, language: str) -> None:
    """Save or update user language in Django DB. Invalidates cache."""

    @_to_async
    def _save():
        from apps.botapp.models import TelegramUser

        TelegramUser.objects.update_or_create(
            chat_id=chat_id,
            defaults={"language": language},
        )

    await _save()
    _lang_cache.set(str(chat_id), language)


async def save_user_profile(
    chat_id: int,
    *,
    full_name: str | None = None,
    phone_number: str | None = None,
    username: str | None = None,
    language: str | None = None,
) -> None:
    """
    Save/update user profile in Django DB (single source of truth).
    Only provided (non-None) fields are updated.
    """

    @_to_async
    def _save():
        from apps.botapp.models import TelegramUser

        defaults = {}
        if full_name is not None:
            defaults["full_name"] = full_name
        if phone_number is not None:
            defaults["phone_number"] = phone_number
        if username is not None:
            defaults["username"] = username
        if language is not None:
            defaults["language"] = language
        if not defaults:
            return
        TelegramUser.objects.update_or_create(
            chat_id=chat_id,
            defaults=defaults,
        )

    await _save()
    if language is not None:
        _lang_cache.set(str(chat_id), language)


async def get_user_profile(chat_id: int) -> dict | None:
    """Get full user profile from Django DB. Returns dict or None."""

    @_to_async
    def _fetch():
        from apps.botapp.models import TelegramUser

        try:
            u = TelegramUser.objects.get(chat_id=chat_id)
            return {
                "chat_id": u.chat_id,
                "full_name": u.full_name,
                "phone_number": u.phone_number,
                "username": u.username,
                "language": u.language,
            }
        except TelegramUser.DoesNotExist:
            return None

    return await _fetch()


async def user_exists(chat_id: int) -> bool:
    """Check if a TelegramUser record exists for this chat_id."""

    @_to_async
    def _check():
        from apps.botapp.models import TelegramUser

        return TelegramUser.objects.filter(chat_id=chat_id).exists()

    return await _check()


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
# Catalog: Flowers — uses apps.catalog.models.Flower (NO cache)
# ---------------------------------------------------------------------------


async def get_active_flowers() -> list:
    """Return all active flowers from Django DB. Always fresh."""

    @_to_async
    def _fetch():
        from apps.catalog.models import Flower

        return list(Flower.objects.filter(is_active=True).order_by("name"))

    return await _fetch()


async def get_flower_by_pk(flower_id: int):
    """Return a single flower by primary key, or None."""

    @_to_async
    def _fetch():
        from apps.catalog.models import Flower

        try:
            return Flower.objects.get(pk=flower_id)
        except Flower.DoesNotExist:
            return None

    return await _fetch()


async def get_flower_services() -> list:
    """Return active services with category='flower'. Always fresh."""

    @_to_async
    def _fetch():
        from apps.catalog.models import Service

        return list(
            Service.objects.filter(is_active=True, category="flower")
            .order_by("name")
        )

    return await _fetch()


# ---------------------------------------------------------------------------
# Price helper
# ---------------------------------------------------------------------------


def format_price(price, lang: str = "en") -> str:
    """Format price (int, Decimal, or float) for display. Assumes UZS sum."""
    return f"{int(price):,} sum".replace(",", " ")

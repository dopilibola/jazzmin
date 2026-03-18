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
# Catalog: Flower categories & products (NO cache — always fresh from DB)
# ---------------------------------------------------------------------------


async def get_active_flower_categories() -> list:
    """Return all active flower categories. Always fresh."""

    @_to_async
    def _fetch():
        from apps.botapp.models import CatalogFlowerCategory

        return list(
            CatalogFlowerCategory.objects.filter(is_active=True)
            .order_by("sort_order", "name_en")
        )

    return await _fetch()


async def get_flower_category_by_pk(category_id: int):
    """Return a single flower category by pk, or None."""

    @_to_async
    def _fetch():
        from apps.botapp.models import CatalogFlowerCategory

        try:
            return CatalogFlowerCategory.objects.get(pk=category_id)
        except CatalogFlowerCategory.DoesNotExist:
            return None

    return await _fetch()


async def get_active_flower_products(category_id: int) -> list:
    """Return active flower products for a given category. Always fresh."""

    @_to_async
    def _fetch():
        from apps.botapp.models import CatalogFlowerProduct

        return list(
            CatalogFlowerProduct.objects.filter(
                category_id=category_id,
                is_active=True,
            ).order_by("name_en")
        )

    return await _fetch()


async def get_flower_product_by_pk(product_id: int):
    """Return a single flower product by pk, or None."""

    @_to_async
    def _fetch():
        from apps.botapp.models import CatalogFlowerProduct

        try:
            return CatalogFlowerProduct.objects.get(pk=product_id)
        except CatalogFlowerProduct.DoesNotExist:
            return None

    return await _fetch()


async def get_all_active_flower_products() -> list:
    """Return ALL active flower products across all categories. Always fresh."""

    @_to_async
    def _fetch():
        from apps.botapp.models import CatalogFlowerProduct

        return list(
            CatalogFlowerProduct.objects.filter(is_active=True)
            .select_related("category")
            .order_by("category__sort_order", "name_en")
        )

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

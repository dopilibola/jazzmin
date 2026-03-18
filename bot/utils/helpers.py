"""
Helper functions: price formatting, etc.
"""
from bot.database.models import Flower, Service
from bot.utils.texts import get_text


def format_grave_date(year: int | None, month: int | None, approximate: bool, lang: str) -> str:
    """Format birth/death date for grave display. E.g. '1950.05' or '1950.05 (taxminan)'."""
    if not year:
        return "—"
    part = f"{year}"
    if month:
        part += f".{month:02d}"
    if approximate:
        part += f" ({get_text(lang, 'btn_approximate')})"
    return part


def format_price(price: int, lang: str = "en") -> str:
    """Format price for display. Assumes UZS sum."""
    return f"{price:,} sum".replace(",", " ")


def get_item_title(item_type: str, item_id: int, service: Service | None, flower: Flower | None, lang: str) -> str:
    """Get localized title for service or flower."""
    if item_type == "service" and service:
        return service.get_name(lang)
    if item_type == "flower" and flower:
        return flower.get_name(lang)
    return f"{item_type}#{item_id}"

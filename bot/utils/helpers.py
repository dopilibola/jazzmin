"""
Helper functions: price formatting, etc.
"""
from apps.botapp.helpers import format_price  # noqa: F401 (re-exported)
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


def get_item_title(item_type: str, item_id: int, lang: str, title: str = "") -> str:
    """Get title for a cart/order item. Uses stored title from cart item."""
    if title:
        return title
    return f"{item_type}#{item_id}"

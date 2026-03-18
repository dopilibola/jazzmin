"""
Cart business logic: totals, formatting.
"""
from bot.database.models import Cart, CartItem
from bot.utils.services_catalog import get_service, get_service_name, format_price


def get_cart_total(cart: Cart) -> int:
    """Calculate total price of cart."""
    return sum(item.quantity * item.unit_price for item in cart.items)


def format_cart_for_display(cart: Cart, lang: str) -> str:
    """
    Format cart contents for user display.
    Returns multiline string with items and total.
    """
    if not cart.items:
        return ""
    lines = []
    for item in cart.items:
        service = get_service(item.service_id)
        name = get_service_name(service, lang) if service else item.service_id
        subtotal = item.quantity * item.unit_price
        lines.append(f"• {name} x{item.quantity} — {format_price(subtotal, lang)}")
    total = get_cart_total(cart)
    lines.append(f"\n<b>Total: {format_price(total, lang)}</b>")
    return "\n".join(lines)

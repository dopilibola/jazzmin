"""
Cart business logic: totals, formatting.
"""
from apps.botapp.helpers import format_price
from bot.database.models import Cart


def get_cart_total(cart: Cart) -> int:
    """Calculate total price of cart."""
    return sum(item.quantity * item.unit_price for item in cart.items)


def format_cart_for_display(cart: Cart, lang: str) -> str:
    """Format cart contents for user display."""
    if not cart.items:
        return ""
    lines = []
    for item in cart.items:
        subtotal = item.quantity * item.unit_price
        lines.append(f"• {item.title} x{item.quantity} — {format_price(subtotal, lang)}")
    total = get_cart_total(cart)
    lines.append(f"\n<b>Total: {format_price(total, lang)}</b>")
    return "\n".join(lines)

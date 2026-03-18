"""
Cart notification service.
Sends confirmation when a product is added to cart, with product details
and action buttons (Continue Shopping, View Cart).
"""
from aiogram.types import CallbackQuery, Message

from bot.utils.helpers import format_price
from bot.utils.texts import get_text


def get_add_to_cart_message(
    lang: str,
    product_name: str,
    price: int,
    quantity: int = 1,
) -> str:
    """
    Build notification message when product is added to cart.
    Includes product name and price. Shows quantity if > 1.
    """
    price_str = format_price(price, lang)
    if quantity > 1:
        return get_text(
            lang,
            "cart_notify_added_with_details_qty",
            product=product_name,
            quantity=quantity,
            price=price_str,
        )
    return get_text(
        lang,
        "cart_notify_added_with_details",
        product=product_name,
        price=price_str,
    )

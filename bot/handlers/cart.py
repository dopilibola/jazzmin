"""
Cart: view items, remove item, clear cart, proceed to checkout.
"""
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.db import async_session_factory
from bot.database.queries import (
    clear_flower_cart,
    get_flower_cart_items,
    get_user_by_telegram_id,
    remove_cart_item,
)
from bot.keyboards.inline import flower_cart_inline
from bot.utils.helpers import format_price
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.texts import get_text

router = Router(name="cart")


async def _get_lang(telegram_id: int) -> str:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


def _format_cart(items: list, lang: str) -> str:
    """Format cart contents for display."""
    lines = []
    for item in items:
        subtotal = item.quantity * item.price
        lines.append(f"• {item.title} x{item.quantity} — {format_price(subtotal, lang)}")
    total = sum(item.quantity * item.price for item in items)
    lines.append(f"\n<b>Total: {format_price(total, lang)}</b>")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Cart: only inside Flowers (no main menu button). Access via flcart:view in flowers.
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Cart callbacks: remove, clear, checkout (legacy cart:* - flower flow uses flcart:*)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data == "cart:view")
async def cart_view_callback(callback: CallbackQuery) -> None:
    """Show flower cart when user clicks 'View Cart' from add-to-cart notification."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await safe_edit_text(callback, get_text(lang, "cart_empty"))
            return
        items = await get_flower_cart_items(session, user.id)
    if not items:
        await safe_edit_text(
            callback,
            get_text(lang, "cart_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    content = _format_cart(items, lang)
    await safe_edit_text(
        callback,
        get_text(lang, "cart_title") + "\n\n" + content,
        reply_markup=flower_cart_inline(lang, items, has_items=True),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("cart:"))
async def cart_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle legacy cart actions (cart now uses flower_cart_inline -> flcart:* in flowers)."""
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await safe_edit_text(callback, get_text(lang, "cart_empty"))
            return
        items = await get_flower_cart_items(session, user.id)

        if data.startswith("cart:remove:"):
            item_id = int(data.replace("cart:remove:", ""))
            removed = await remove_cart_item(session, item_id, user.id)
            await session.commit()
            if removed:
                items = await get_flower_cart_items(session, user.id)
                if not items:
                    await safe_edit_text(
                        callback,
                        get_text(lang, "cart_title") + "\n\n" + get_text(lang, "cart_empty"),
                    )
                    return
                content = _format_cart(items, lang)
                await safe_edit_text(
                    callback,
                    get_text(lang, "cart_title") + "\n\n" + content,
                    reply_markup=flower_cart_inline(lang, items, has_items=True),
                )
            return

        if data == "cart:clear":
            await clear_flower_cart(session, user.id)
            await session.commit()
            await safe_edit_text(
                callback,
                get_text(lang, "cart_title") + "\n\n" + get_text(lang, "cart_empty"),
            )
            return

        if data == "cart:checkout":
            if not items:
                await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
                return
            from bot.handlers.flowers import _start_flower_checkout_from_cart

            await _start_flower_checkout_from_cart(callback, state)

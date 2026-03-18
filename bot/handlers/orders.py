"""
My Orders: list orders, view detail.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.database.db import async_session_factory
from bot.database.queries import get_orders_by_user, get_order_by_id, get_user_by_telegram_id
from bot.keyboards.inline import order_detail_inline, order_list_inline
from bot.keyboards.reply import main_menu_keyboard
from bot.utils.helpers import format_price
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.texts import get_status_label, get_text

router = Router(name="orders")


async def _get_lang(telegram_id: int) -> str:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


def _format_order_list_item(order, lang: str) -> str:
    """Format order for list display."""
    status_label = get_status_label(lang, order.status)
    date_str = order.created_at.strftime("%d.%m.%Y") if order.created_at else ""
    total_str = format_price(getattr(order, "total_price", 0) or 0, lang)
    return (
        get_text(lang, "order_item", id=order.id, status=status_label, date=date_str)
        + f" — {total_str}"
    )


def _format_order_detail(order, lang: str) -> str:
    """Format full order detail."""
    status_label = get_status_label(lang, order.status)
    total_str = format_price(order.total_price, lang)
    details = []
    if order.region and order.district and order.cemetery:
        details.append(
            get_text(
                lang,
                "order_detail_location",
                region=order.region.get_name(lang),
                district=order.district.get_name(lang),
                cemetery=order.cemetery.name,
            )
        )
    if order.deceased_full_name:
        birth = str(order.birth_year) if order.birth_year else "?"
        death = str(order.death_year) if order.death_year else "?"
        details.append(
            get_text(
                lang,
                "order_detail_deceased",
                name=order.deceased_full_name,
                birth=birth,
                death=death,
            )
        )
    items_lines = []
    for item in order.items:
        items_lines.append(f"  • {item.title} x{item.quantity} — {format_price(item.quantity * item.price, lang)}")
    details.append(
        get_text(lang, "order_detail_services", services="\n".join(items_lines))
    )
    details_str = "\n\n".join(details)
    return get_text(
        lang,
        "order_detail",
        id=order.id,
        status=status_label,
        details=details_str,
        total=total_str,
        photo_count="0",
    )


# -----------------------------------------------------------------------------
# My Orders from main menu
# -----------------------------------------------------------------------------


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_order_history"),
            get_text("ru", "btn_order_history"),
            get_text("uz", "btn_order_history"),
        ]
    )
)
async def show_order_list(message: Message) -> None:
    """Show list of user orders."""
    telegram_id = message.from_user.id
    lang = await _get_lang(telegram_id)
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await message.answer(
                get_text(lang, "order_history_empty"),
                reply_markup=main_menu_keyboard(lang),
            )
            return
        orders = await get_orders_by_user(session, user.id)
    if not orders:
        await message.answer(
            get_text(lang, "order_history_empty"),
            reply_markup=main_menu_keyboard(lang),
        )
        return
    lines = [_format_order_list_item(o, lang) for o in orders]
    text = get_text(lang, "order_history_title") + "\n\n" + "\n\n".join(lines)
    await message.answer(
        text,
        reply_markup=order_list_inline(orders, lang),
    )


# -----------------------------------------------------------------------------
# Order detail (callback)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and (c.data == "order:list" or c.data.startswith("order:detail:")))
async def order_callback(callback: CallbackQuery) -> None:
    """Handle order:detail:ID, order:list."""
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id

    # Back to list
    if data == "order:list":
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            if not user:
                return
            orders = await get_orders_by_user(session, user.id)
        if not orders:
            await safe_edit_text(callback, get_text(lang, "order_history_empty"))
            return
        lines = [_format_order_list_item(o, lang) for o in orders]
        text = get_text(lang, "order_history_title") + "\n\n" + "\n\n".join(lines)
        await safe_edit_text(
            callback,
            text,
            reply_markup=order_list_inline(orders, lang),
        )
        return

    if data.startswith("order:detail:"):
        order_id = int(data.replace("order:detail:", ""))
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            if not user:
                return
            order = await get_order_by_id(session, order_id)
            if not order or order.user_id != user.id:
                await callback.answer(get_text(lang, "order_history_empty"), show_alert=True)
                return
        text = _format_order_detail(order, lang)
        await safe_edit_text(
            callback,
            text,
            reply_markup=order_detail_inline(lang, order_id),
        )

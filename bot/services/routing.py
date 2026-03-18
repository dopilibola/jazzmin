"""
Routing service: resolve district to operator group and send orders.
Supports both config (OPERATOR_GROUPS from .env) and database (OperatorGroup).
"""
from typing import TYPE_CHECKING

from aiogram import Bot

from bot.database.models import Cemetery, Order
from bot.keyboards.inline import operator_take_order_inline
from bot.utils.texts import get_text
from bot_config import OPERATOR_GROUPS

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def get_operator_group_from_config(district_id: int) -> int | None:
    """
    Get Telegram group chat ID for a district from config (.env).
    Returns None if not configured.
    """
    return OPERATOR_GROUPS.get(district_id)


async def get_operator_group_id(
    session: "AsyncSession", district_id: int
) -> int | None:
    """
    Get Telegram group chat ID for a district.
    Tries database (OperatorGroup) first, then config.
    Returns None if neither is configured.
    """
    from bot.database.queries import get_telegram_group_for_district

    group_id = await get_telegram_group_for_district(session, district_id)
    if group_id is not None:
        return group_id
    return get_operator_group_from_config(district_id)


async def send_order_to_operator_group(
    bot: Bot,
    order: Order,
    cemetery: Cemetery,
    lang: str,
    group_chat_id: int | None,
) -> bool:
    """
    Send order card with "Take Order" button to the district operator group.
    Returns True if sent, False if group_chat_id is None or send fails.
    """
    if group_chat_id is None:
        return False
    text = get_text(
        lang,
        "operator_order_card",
        order_id=order.id,
        customer_name=order.user.full_name,
        phone=order.user.phone_number,
        cemetery=cemetery.name,
        deceased_full_name=order.deceased_full_name,
        birth_year=order.birth_year,
        death_year=order.death_year,
    )
    kb = operator_take_order_inline(order.id)
    try:
        await bot.send_message(
            chat_id=group_chat_id, text=text, reply_markup=kb
        )
        return True
    except Exception:
        return False

"""
Notification helpers. Forward user messages (complaints, support) to admins.
Admin IDs loaded from ADMIN_IDS in .env via config.
"""
from aiogram import Bot

from bot.services.admin import get_admin_ids


def format_user_message(
    *,
    prefix: str,
    user_id: int,
    user_name: str,
    user_phone: str,
    message_text: str,
) -> str:
    """
    Format a user message for admin notification.
    Includes: telegram ID, full name (if available), phone (if available), message.
    """
    name = user_name.strip() if user_name else "—"
    phone = user_phone.strip() if user_phone else "—"
    if name == "Unknown" or not name:
        name = "—"
    return (
        f"📩 {prefix}\n\n"
        f"👤 User ID: {user_id}\n"
        f"📛 Full name: {name}\n"
        f"📞 Phone: {phone}\n\n"
        f"💬 Message:\n{message_text}"
    )


async def forward_complaint_to_admins(
    bot: Bot,
    user_id: int,
    user_name: str,
    user_phone: str,
    text: str,
) -> None:
    """
    Forward a complaint/suggestion to all admins.
    User info: telegram ID, full name if available, phone if available.
    """
    admin_ids = get_admin_ids()
    if not admin_ids:
        return
    msg = format_user_message(
        prefix="COMPLAINT / SUGGESTION",
        user_id=user_id,
        user_name=user_name or "—",
        user_phone=user_phone or "—",
        message_text=text,
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=msg)
        except Exception:
            pass  # Log in production if needed


async def forward_support_to_admins(
    bot: Bot,
    user_id: int,
    user_name: str,
    user_phone: str,
    text: str,
) -> None:
    """
    Forward a support message to all admins.
    Same concept as complaint forwarding.
    """
    admin_ids = get_admin_ids()
    if not admin_ids:
        return
    msg = format_user_message(
        prefix="SUPPORT REQUEST",
        user_id=user_id,
        user_name=user_name or "—",
        user_phone=user_phone or "—",
        message_text=text,
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=msg)
        except Exception:
            pass

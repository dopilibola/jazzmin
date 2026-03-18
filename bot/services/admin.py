"""
Admin helper functions.
Admin IDs are loaded from .env via config.ADMIN_IDS.
"""
from bot_config import ADMIN_IDS


def get_admin_ids() -> list[int]:
    """
    Get list of valid admin Telegram user IDs.
    Returns empty list if none configured.
    """
    return list(ADMIN_IDS)


def is_admin(telegram_id: int) -> bool:
    """Check if the given Telegram user ID is an admin."""
    return telegram_id in ADMIN_IDS


def has_admins_configured() -> bool:
    """Check if at least one admin ID is configured."""
    return len(ADMIN_IDS) > 0

"""
Configuration module for the Telegram bot.
Loads settings from the same .env file as Django.
Admin IDs are validated and loaded safely.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

logger = logging.getLogger(__name__)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

_TELEGRAM_ID_MIN = 1
_TELEGRAM_ID_MAX = 2**63 - 1


def _parse_admin_ids() -> list[int]:
    """
    Parse and validate admin IDs from ADMIN_IDS env variable.
    Format: comma-separated integers (e.g. "123456789,987654321")
    Invalid entries are logged and skipped.
    """
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        raw = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    if not raw:
        logger.warning("ADMIN_IDS is empty. Complaints and support messages will not be forwarded.")
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            uid = int(part)
            if uid < _TELEGRAM_ID_MIN or uid > _TELEGRAM_ID_MAX:
                logger.warning("Admin ID %s out of valid range, skipping.", part)
                continue
            if uid in ids:
                continue
            ids.append(uid)
        except ValueError:
            logger.warning("Invalid admin ID '%s' (not a number), skipping.", part)
    if not ids:
        logger.warning("No valid admin IDs found in ADMIN_IDS.")
    return ids


ADMIN_IDS: list[int] = _parse_admin_ids()

# Database — use same PostgreSQL as Django
_db_user = os.getenv("DB_USER", "")
_db_pass = os.getenv("DB_PASSWORD", "")
_db_host = os.getenv("DB_HOST", "127.0.0.1")
_db_port = os.getenv("DB_PORT", "5432")
_db_name = os.getenv("DB_NAME", "")

if _db_host == "db" and not os.path.exists("/.dockerenv"):
    _db_host = "127.0.0.1"

if _db_user and _db_name:
    _default_url = f"postgresql+asyncpg://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}"
else:
    _default_url = "sqlite+aiosqlite:///./data/grave_service.db"

DATABASE_URL: str = os.getenv("DATABASE_URL", _default_url).strip()

if "sqlite" in DATABASE_URL:
    _path = Path(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
    if _path.suffix:
        _path.parent.mkdir(parents=True, exist_ok=True)

# Google Sheets (user registration sync)
SPREADSHEET_ID: str = os.getenv(
    "GOOGLE_SPREADSHEET_ID", "1ChnBZ88Tdi8TJN6lwQaWwHqci9tcvLEDQV3JFKbdHBQ"
).strip()
GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "").strip()

# Support link
SUPPORT_LINK: str = os.getenv("SUPPORT_LINK", "").strip()

# Payment card numbers
PAYMENT_CARD_NUMBER: str = os.getenv("PAYMENT_CARD_NUMBER", "").strip()
PAYMENT_CARD_INTERNAL: str = os.getenv("PAYMENT_CARD_INTERNAL", "").strip()
PAYMENT_CARD_INTERNATIONAL: str = os.getenv("PAYMENT_CARD_INTERNATIONAL", "").strip()

# Payment receipts group
PAYMENT_GROUP_ID: str = os.getenv("PAYMENT_GROUP_ID", "").strip()

# Payment channel
PAYMENT_CHANNEL_ID: str = os.getenv("PAYMENT_CHANNEL_ID", "").strip()

# Payment verification bot token (BOT_TOKEN3)
PAYMENT_BOT_TOKEN: str = os.getenv("BOT_TOKEN3", "").strip()

# Operator groups: district_id -> Telegram group chat ID (comma-separated pairs)
def _parse_operator_groups() -> dict[int, int]:
    raw = os.getenv("OPERATOR_GROUPS", "").strip()
    if not raw:
        return {}
    groups: dict[int, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        try:
            district_id, group_id = pair.split(":", 1)
            groups[int(district_id.strip())] = int(group_id.strip())
        except (ValueError, IndexError):
            continue
    return groups


OPERATOR_GROUPS: dict[int, int] = _parse_operator_groups()

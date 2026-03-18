"""
Google Sheets integration for user registration data.
Appends new user data to the configured spreadsheet.
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy import to avoid errors when gspread not installed
_gspread = None
_credentials = None


def _get_gspread():
    global _gspread
    if _gspread is None:
        try:
            import gspread
            _gspread = gspread
        except ImportError:
            logger.warning("gspread not installed. Google Sheets sync disabled.")
    return _gspread


async def append_user_to_sheet(
    spreadsheet_id: str,
    credentials_path: str,
    telegram_id: int,
    full_name: str,
    phone_number: str,
    username: str | None = None,
) -> bool:
    """
    Append user registration data to Google Sheet.
    Runs in thread pool to avoid blocking.
    Returns True on success, False on failure.
    """
    gs = _get_gspread()
    if not gs:
        return False
    if not spreadsheet_id or not credentials_path:
        logger.warning("Google Sheets not configured (SPREADSHEET_ID or GOOGLE_CREDENTIALS_PATH).")
        return False

    cred_path = Path(credentials_path)
    if not cred_path.exists():
        logger.warning("Google credentials file not found: %s", credentials_path)
        return False

    def _sync_append():
        from google.oauth2.service_account import Credentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(cred_path), scopes=scope)
        gc = gs.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        wks = sh.sheet1
        row = [
            str(telegram_id),
            full_name,
            phone_number,
            username or "",
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ]
        wks.append_row(row, value_input_option="USER_ENTERED")
        return True

    try:
        await asyncio.to_thread(_sync_append)
        logger.info("User %s appended to Google Sheet.", telegram_id)
        return True
    except Exception as e:
        logger.exception("Failed to append user to Google Sheet: %s", e)
        return False

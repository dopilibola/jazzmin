"""
Google Sheets integration for user data sync.
Mirrors user profile data from Django DB to Google Sheets.
- New user → append row
- Existing user → update row in place
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_gspread = None


def _get_gspread():
    global _gspread
    if _gspread is None:
        try:
            import gspread
            _gspread = gspread
        except ImportError:
            logger.warning("gspread not installed. Google Sheets sync disabled.")
    return _gspread


def _get_worksheet(spreadsheet_id: str, credentials_path: str):
    """Authorize and return the first worksheet."""
    gs = _get_gspread()
    if not gs:
        return None
    from google.oauth2.service_account import Credentials
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
    gc = gs.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    return sh.sheet1


HEADER_ROW = ["Telegram ID", "Ism", "Telefon", "Username", "Til", "Sana"]


def _ensure_header(wks):
    """Ensure the first row has proper headers."""
    try:
        first_row = wks.row_values(1)
        if not first_row or first_row[0] != HEADER_ROW[0]:
            wks.insert_row(HEADER_ROW, 1)
    except Exception:
        pass


def _find_user_row(wks, telegram_id: str) -> int | None:
    """Find the row number for a telegram_id. Returns None if not found."""
    try:
        cell = wks.find(telegram_id, in_column=1)
        if cell:
            return cell.row
    except Exception:
        pass
    return None


async def sync_user_to_sheet(
    spreadsheet_id: str,
    credentials_path: str,
    *,
    telegram_id: int,
    full_name: str = "",
    phone_number: str = "",
    username: str = "",
    language: str = "uz",
) -> bool:
    """
    Sync user data to Google Sheet.
    - If user row exists → update it
    - If not → append new row
    Returns True on success, False on failure.
    """
    gs = _get_gspread()
    if not gs:
        return False
    if not spreadsheet_id or not credentials_path:
        logger.warning("Google Sheets not configured.")
        return False

    cred_path = Path(credentials_path)
    if not cred_path.exists():
        logger.warning("Google credentials file not found: %s", credentials_path)
        return False

    def _sync():
        wks = _get_worksheet(spreadsheet_id, credentials_path)
        if not wks:
            return False

        _ensure_header(wks)

        tid_str = str(telegram_id)
        row_data = [
            tid_str,
            full_name,
            phone_number,
            username or "",
            language,
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ]

        existing_row = _find_user_row(wks, tid_str)
        if existing_row:
            # Update existing row
            for col, value in enumerate(row_data, start=1):
                wks.update_cell(existing_row, col, value)
        else:
            # Append new row
            wks.append_row(row_data, value_input_option="USER_ENTERED")
        return True

    try:
        result = await asyncio.to_thread(_sync)
        logger.info("User %s synced to Google Sheet.", telegram_id)
        return result
    except Exception as e:
        logger.exception("Failed to sync user to Google Sheet: %s", e)
        return False


# Backward compatibility alias
async def append_user_to_sheet(
    spreadsheet_id: str,
    credentials_path: str,
    telegram_id: int,
    full_name: str,
    phone_number: str,
    username: str | None = None,
) -> bool:
    """Backward-compatible wrapper. Use sync_user_to_sheet instead."""
    return await sync_user_to_sheet(
        spreadsheet_id,
        credentials_path,
        telegram_id=telegram_id,
        full_name=full_name,
        phone_number=phone_number,
        username=username or "",
    )

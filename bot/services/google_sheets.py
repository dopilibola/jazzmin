"""
Google Sheets integration for tracking user data and graves.
Each user's graves are stored in rows with their telegram_id for filtering.
"""
import logging
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from bot_config import GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Sheet names
USERS_SHEET = "Users"
GRAVES_SHEET = "Graves"
ORDERS_SHEET = "Orders"

# Cache for gspread client
_client: Optional[gspread.Client] = None
_spreadsheet: Optional[gspread.Spreadsheet] = None


def _get_client() -> Optional[gspread.Client]:
    """Get or create gspread client."""
    global _client

    if _client:
        return _client

    if not GOOGLE_SHEETS_CREDENTIALS:
        logger.warning("GOOGLE_SHEETS_CREDENTIALS not configured")
        return None

    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS,
            scopes=SCOPES
        )
        _client = gspread.authorize(creds)
        return _client
    except Exception as e:
        logger.error(f"Failed to create Google Sheets client: {e}")
        return None


def _get_spreadsheet() -> Optional[gspread.Spreadsheet]:
    """Get or open the spreadsheet."""
    global _spreadsheet

    if _spreadsheet:
        return _spreadsheet

    client = _get_client()
    if not client:
        return None

    if not GOOGLE_SHEETS_ID:
        logger.warning("GOOGLE_SHEETS_ID not configured")
        return None

    try:
        _spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        return _spreadsheet
    except Exception as e:
        logger.error(f"Failed to open spreadsheet: {e}")
        return None


def _get_or_create_sheet(name: str, headers: list[str]) -> Optional[gspread.Worksheet]:
    """Get or create a worksheet with headers."""
    spreadsheet = _get_spreadsheet()
    if not spreadsheet:
        return None

    try:
        # Try to get existing sheet
        try:
            sheet = spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            # Create new sheet with headers
            sheet = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
            sheet.append_row(headers)
            logger.info(f"Created new sheet: {name}")

        return sheet
    except Exception as e:
        logger.error(f"Failed to get/create sheet {name}: {e}")
        return None


# -----------------------------------------------------------------------------
# User tracking
# -----------------------------------------------------------------------------

USERS_HEADERS = [
    "telegram_id",
    "username",
    "full_name",
    "phone_number",
    "language",
    "registered_at",
    "last_active",
    "total_graves",
    "total_orders",
]


async def log_user(
    telegram_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    language: str = "uz",
) -> bool:
    """Log or update user in Google Sheets."""
    try:
        sheet = _get_or_create_sheet(USERS_SHEET, USERS_HEADERS)
        if not sheet:
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if user exists
        try:
            cell = sheet.find(str(telegram_id), in_column=1)
            if cell:
                # Update existing user
                row = cell.row
                sheet.update_cell(row, 2, username or "")
                sheet.update_cell(row, 3, full_name or "")
                sheet.update_cell(row, 4, phone_number or "")
                sheet.update_cell(row, 5, language)
                sheet.update_cell(row, 7, now)  # last_active
                logger.info(f"Updated user {telegram_id} in Google Sheets")
                return True
        except gspread.exceptions.CellNotFound:
            pass

        # Add new user
        row_data = [
            str(telegram_id),
            username or "",
            full_name or "",
            phone_number or "",
            language,
            now,  # registered_at
            now,  # last_active
            0,    # total_graves
            0,    # total_orders
        ]
        sheet.append_row(row_data)
        logger.info(f"Added new user {telegram_id} to Google Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to log user {telegram_id}: {e}")
        return False


async def update_user_stats(telegram_id: int, graves_count: int = 0, orders_count: int = 0) -> bool:
    """Update user's grave and order counts."""
    try:
        sheet = _get_or_create_sheet(USERS_SHEET, USERS_HEADERS)
        if not sheet:
            return False

        try:
            cell = sheet.find(str(telegram_id), in_column=1)
            if cell:
                row = cell.row
                if graves_count:
                    current = int(sheet.cell(row, 8).value or 0)
                    sheet.update_cell(row, 8, current + graves_count)
                if orders_count:
                    current = int(sheet.cell(row, 9).value or 0)
                    sheet.update_cell(row, 9, current + orders_count)
                return True
        except gspread.exceptions.CellNotFound:
            pass

        return False
    except Exception as e:
        logger.error(f"Failed to update user stats: {e}")
        return False


# -----------------------------------------------------------------------------
# Grave tracking
# -----------------------------------------------------------------------------

GRAVES_HEADERS = [
    "id",
    "telegram_id",
    "username",
    "deceased_full_name",
    "relationship",
    "birth_year",
    "death_year",
    "region",
    "district",
    "cemetery",
    "row_number",
    "created_at",
    "updated_at",
]


async def log_grave(
    grave_id: int,
    telegram_id: int,
    username: Optional[str] = None,
    deceased_full_name: Optional[str] = None,
    relationship: Optional[str] = None,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
    region: Optional[str] = None,
    district: Optional[str] = None,
    cemetery: Optional[str] = None,
    row_number: Optional[str] = None,
) -> bool:
    """Log a grave entry to Google Sheets."""
    try:
        sheet = _get_or_create_sheet(GRAVES_SHEET, GRAVES_HEADERS)
        if not sheet:
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if grave exists
        try:
            cell = sheet.find(str(grave_id), in_column=1)
            if cell:
                # Update existing grave
                row = cell.row
                sheet.update_cell(row, 4, deceased_full_name or "")
                sheet.update_cell(row, 5, relationship or "")
                sheet.update_cell(row, 6, birth_year or "")
                sheet.update_cell(row, 7, death_year or "")
                sheet.update_cell(row, 8, region or "")
                sheet.update_cell(row, 9, district or "")
                sheet.update_cell(row, 10, cemetery or "")
                sheet.update_cell(row, 11, row_number or "")
                sheet.update_cell(row, 13, now)  # updated_at
                logger.info(f"Updated grave {grave_id} in Google Sheets")
                return True
        except gspread.exceptions.CellNotFound:
            pass

        # Add new grave
        row_data = [
            str(grave_id),
            str(telegram_id),
            username or "",
            deceased_full_name or "",
            relationship or "",
            str(birth_year) if birth_year else "",
            str(death_year) if death_year else "",
            region or "",
            district or "",
            cemetery or "",
            row_number or "",
            now,  # created_at
            now,  # updated_at
        ]
        sheet.append_row(row_data)
        logger.info(f"Added grave {grave_id} for user {telegram_id} to Google Sheets")

        # Update user's grave count
        await update_user_stats(telegram_id, graves_count=1)

        return True

    except Exception as e:
        logger.error(f"Failed to log grave {grave_id}: {e}")
        return False


async def get_user_graves(telegram_id: int) -> list[dict]:
    """Get all graves for a specific user."""
    try:
        sheet = _get_or_create_sheet(GRAVES_SHEET, GRAVES_HEADERS)
        if not sheet:
            return []

        # Get all records
        records = sheet.get_all_records()

        # Filter by telegram_id
        user_graves = [
            r for r in records
            if str(r.get("telegram_id", "")) == str(telegram_id)
        ]

        return user_graves

    except Exception as e:
        logger.error(f"Failed to get graves for user {telegram_id}: {e}")
        return []


# -----------------------------------------------------------------------------
# Order tracking
# -----------------------------------------------------------------------------

ORDERS_HEADERS = [
    "order_id",
    "telegram_id",
    "username",
    "full_name",
    "phone_number",
    "grave_id",
    "deceased_name",
    "cemetery",
    "services",
    "total_price",
    "status",
    "worker_username",
    "created_at",
    "completed_at",
    "feedback",
]


async def log_order(
    order_id: int,
    telegram_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    grave_id: Optional[int] = None,
    deceased_name: Optional[str] = None,
    cemetery: Optional[str] = None,
    services: Optional[str] = None,
    total_price: int = 0,
    status: str = "new",
) -> bool:
    """Log an order to Google Sheets."""
    try:
        sheet = _get_or_create_sheet(ORDERS_SHEET, ORDERS_HEADERS)
        if not sheet:
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if order exists
        try:
            cell = sheet.find(str(order_id), in_column=1)
            if cell:
                # Update existing order
                row = cell.row
                sheet.update_cell(row, 10, total_price)
                sheet.update_cell(row, 11, status)
                logger.info(f"Updated order {order_id} in Google Sheets")
                return True
        except gspread.exceptions.CellNotFound:
            pass

        # Add new order
        row_data = [
            str(order_id),
            str(telegram_id),
            username or "",
            full_name or "",
            phone_number or "",
            str(grave_id) if grave_id else "",
            deceased_name or "",
            cemetery or "",
            services or "",
            str(total_price),
            status,
            "",  # worker_username
            now,  # created_at
            "",  # completed_at
            "",  # feedback
        ]
        sheet.append_row(row_data)
        logger.info(f"Added order {order_id} for user {telegram_id} to Google Sheets")

        # Update user's order count
        await update_user_stats(telegram_id, orders_count=1)

        return True

    except Exception as e:
        logger.error(f"Failed to log order {order_id}: {e}")
        return False


async def update_order_in_sheets(
    order_id: int,
    status: str,
    worker_username: Optional[str] = None,
    feedback: Optional[str] = None,
    completed: bool = False,
) -> bool:
    """Update order status in Google Sheets."""
    try:
        sheet = _get_or_create_sheet(ORDERS_SHEET, ORDERS_HEADERS)
        if not sheet:
            return False

        try:
            cell = sheet.find(str(order_id), in_column=1)
            if cell:
                row = cell.row
                sheet.update_cell(row, 11, status)
                if worker_username:
                    sheet.update_cell(row, 12, worker_username)
                if completed:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.update_cell(row, 14, now)
                if feedback:
                    sheet.update_cell(row, 15, feedback)
                logger.info(f"Updated order {order_id} status to {status}")
                return True
        except gspread.exceptions.CellNotFound:
            pass

        return False
    except Exception as e:
        logger.error(f"Failed to update order status: {e}")
        return False


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------


def test_connection() -> bool:
    """Test Google Sheets connection."""
    try:
        spreadsheet = _get_spreadsheet()
        if spreadsheet:
            logger.info(f"Connected to spreadsheet: {spreadsheet.title}")
            return True
        return False
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


# -----------------------------------------------------------------------------
# Legacy sync function (for compatibility with existing handlers)
# -----------------------------------------------------------------------------


async def sync_user_to_sheet(
    spreadsheet_id: str,
    credentials_path: str,
    telegram_id: int,
    full_name: str = "",
    phone_number: str = "",
    language: str = "uz",
    username: str = "",
) -> bool:
    """Legacy function for syncing user to Google Sheets.

    Maintains backward compatibility with existing handlers.
    Uses the new log_user function internally.
    """
    # Override global settings temporarily if different
    global _client, _spreadsheet, GOOGLE_SHEETS_ID, GOOGLE_SHEETS_CREDENTIALS

    try:
        # Use provided credentials if they differ
        if credentials_path and credentials_path != GOOGLE_SHEETS_CREDENTIALS:
            creds = Credentials.from_service_account_file(
                credentials_path,
                scopes=SCOPES
            )
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(spreadsheet_id)

            # Get or create Users sheet
            try:
                sheet = spreadsheet.worksheet(USERS_SHEET)
            except gspread.WorksheetNotFound:
                sheet = spreadsheet.add_worksheet(title=USERS_SHEET, rows=1000, cols=len(USERS_HEADERS))
                sheet.append_row(USERS_HEADERS)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check if user exists
            try:
                cell = sheet.find(str(telegram_id), in_column=1)
                if cell:
                    row = cell.row
                    if full_name:
                        sheet.update_cell(row, 3, full_name)
                    if phone_number:
                        sheet.update_cell(row, 4, phone_number)
                    if language:
                        sheet.update_cell(row, 5, language)
                    if username:
                        sheet.update_cell(row, 2, username)
                    sheet.update_cell(row, 7, now)
                    logger.info(f"Updated user {telegram_id} in Google Sheets (legacy)")
                    return True
            except gspread.exceptions.CellNotFound:
                pass

            # Add new user
            row_data = [
                str(telegram_id),
                username or "",
                full_name or "",
                phone_number or "",
                language,
                now,
                now,
                0,
                0,
            ]
            sheet.append_row(row_data)
            logger.info(f"Added user {telegram_id} to Google Sheets (legacy)")
            return True
        else:
            # Use the standard log_user function
            return await log_user(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                phone_number=phone_number,
                language=language,
            )
    except Exception as e:
        logger.error(f"Failed to sync user to sheet: {e}")
        return False

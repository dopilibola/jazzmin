"""
Validation helpers for customer input.
"""


def is_valid_full_name(text: str, min_length: int = 2) -> bool:
    """Check if full name is valid (not too short)."""
    return bool(text and text.strip() and len(text.strip()) >= min_length)


def is_valid_phone(text: str) -> bool:
    """Check if text looks like a phone number."""
    if not text or len(text) < 9:
        return False
    digits = "".join(c for c in text if c.isdigit())
    return len(digits) >= 9


def normalize_phone(text: str) -> str:
    """Extract digits and format with + prefix."""
    digits = "".join(c for c in text if c.isdigit())
    return "+" + digits if digits and not text.strip().startswith("+") else digits


def is_valid_year(text: str, min_year: int = 1900, max_year: int = 2100) -> bool:
    """Check if text is a valid 4-digit year."""
    if not text or len(text.strip()) != 4:
        return False
    try:
        year = int(text.strip())
        return min_year <= year <= max_year
    except ValueError:
        return False


def is_valid_month(text: str) -> bool:
    """Check if text is a valid month (1-12)."""
    if not text or not text.strip().isdigit():
        return False
    try:
        month = int(text.strip())
        return 1 <= month <= 12
    except ValueError:
        return False

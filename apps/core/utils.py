import re
from decimal import Decimal


def validate_phone_number(phone: str) -> bool:
    cleaned = re.sub(r'[\s\-\(\)]+', '', phone)
    return bool(re.match(r'^\+?\d{7,15}$', cleaned))


def format_price(price) -> str:
    if isinstance(price, Decimal):
        return f"{price:.2f}"
    return f"{float(price):.2f}"

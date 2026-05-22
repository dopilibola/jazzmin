"""Parol/PIN hashlash va telefon raqamini normallashtirish (qo'shimcha kutubxonasiz)."""
import hashlib
import hmac
import os

_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """PIN/parolni pbkdf2-sha256 bilan hashlaydi. Natija: 'salt$hash'."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Kiritilgan parol saqlangan hash'ga mos kelishini tekshiradi."""
    if not stored or "$" not in stored:
        return False
    salt_hex, hash_hex = stored.split("$", 1)
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return hmac.compare_digest(dk.hex(), hash_hex)


def normalize_phone(phone: str) -> str:
    """Telefon raqamidan faqat raqamlarni qoldiradi (998901234567 ko'rinishida)."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    # 9 xonali bo'lsa (901234567) — O'zbekiston kodi qo'shamiz
    if len(digits) == 9:
        digits = "998" + digits
    return digits

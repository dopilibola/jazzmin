"""Saytga kirish uchun bir martalik tasdiqlash kodlari (xotirada, qisqa muddatli)."""
import random
import time

_TTL = 300  # kod 5 daqiqa amal qiladi
_MAX_ATTEMPTS = 5

# telegram_id (str) -> [code, expires_ts, attempts]
_codes: dict[str, list] = {}


def generate_code(key: str) -> str:
    """6 xonali tasdiqlash kodi yaratadi va saqlaydi."""
    code = f"{random.randint(0, 999999):06d}"
    _codes[key] = [code, time.time() + _TTL, 0]
    return code


def verify_code(key: str, code: str) -> bool:
    """Kodni tekshiradi. To'g'ri bo'lsa o'chiradi va True qaytaradi."""
    entry = _codes.get(key)
    if not entry:
        return False
    stored, expires, attempts = entry
    if time.time() > expires or attempts >= _MAX_ATTEMPTS:
        _codes.pop(key, None)
        return False
    entry[2] += 1
    if stored == (code or "").strip():
        _codes.pop(key, None)
        return True
    return False

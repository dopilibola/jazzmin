"""Veb-ilova sozlamalari — .env dan o'qiladi (bot bilan bir xil fayl)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Sessiya cookie'sini imzolash kaliti
SECRET_KEY = (
    os.getenv("WEBAPP_SECRET_KEY")
    or os.getenv("SECRET_KEY")
    or "dev-only-insecure-secret-change-me"
)

# To'lov karta raqamlari (bot bilan bir xil .env dan)
PAYMENT_CARD_INTERNAL = os.getenv("PAYMENT_CARD_INTERNAL", "").strip()
PAYMENT_CARD_INTERNATIONAL = os.getenv("PAYMENT_CARD_INTERNATIONAL", "").strip()
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "").strip()

# Support uchun Telegram username
SUPPORT_USERNAME = os.getenv("lichka", "").strip().lstrip("@")

# Telegram bot tokeni — saytga kirish kodini yuborish uchun
BOT_TOKEN = (os.getenv("BOT_TOKEN", "") or "").strip().strip("'\"")

# Chiqishdan keyin yo'naltiriladigan asl "about" sayt manzili (front Django, domen ildizi)
FRONT_URL = (os.getenv("FRONT_URL") or os.getenv("SITE_URL") or "/").strip()

# To'lov tasdiqlash boti (BOT_TOKEN3) — chekni adminlarga yuborish uchun
PAYMENT_BOT_TOKEN = (os.getenv("BOT_TOKEN3", "") or "").strip().strip("'\"")


def _parse_admin_ids() -> list[int]:
    """ADMIN_IDS ni .env dan o'qiydi (vergul bilan ajratilgan Telegram ID'lar)."""
    raw = (os.getenv("ADMIN_IDS") or os.getenv("TELEGRAM_ADMIN_CHAT_ID") or "")
    raw = raw.strip().strip("'\"")
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


# Chek tasdiqlash uchun admin Telegram ID'lari
ADMIN_IDS = _parse_admin_ids()

# Yuklangan to'lov cheklari shu yerga saqlanadi
UPLOAD_DIR = BASE_DIR / "uploads" / "receipts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

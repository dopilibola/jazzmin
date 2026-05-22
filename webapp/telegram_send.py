"""Telegram bot orqali xabar/chek yuborish."""
import json
import logging

import aiohttp

from webapp.config import ADMIN_IDS, BOT_TOKEN, PAYMENT_BOT_TOKEN

logger = logging.getLogger(__name__)


async def send_code_to_telegram(telegram_id: int, code: str) -> bool:
    """Foydalanuvchining Telegramiga kirish kodini yuboradi. Muvaffaqiyatda True."""
    if not BOT_TOKEN or not telegram_id:
        return False
    text = (
        "🔐 <b>Maskan saytiga kirish kodi</b>\n\n"
        f"Kod: <b><code>{code}</code></b>\n\n"
        "Bu kodni hech kimga bermang. Kod 5 daqiqa amal qiladi."
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    return True
                logger.warning("Telegram sendMessage failed: %s %s",
                               resp.status, await resp.text())
                return False
    except Exception:  # noqa: BLE001
        logger.exception("send_code_to_telegram failed for %s", telegram_id)
        return False


async def fetch_telegram_file(file_id: str) -> bytes | None:
    """Telegram file_id bo'yicha fayl baytlarini yuklab oladi (rasm ko'rsatish uchun)."""
    if not BOT_TOKEN or not file_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 1) getFile — file_path ni aniqlaymiz
            async with session.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
            if not data.get("ok"):
                return None
            file_path = data["result"].get("file_path")
            if not file_path:
                return None
            # 2) faylning o'zini yuklaymiz
            async with session.get(
                f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            ) as resp2:
                if resp2.status != 200:
                    return None
                return await resp2.read()
    except Exception:  # noqa: BLE001
        logger.exception("fetch_telegram_file failed for %s", file_id)
        return None


async def send_receipt_for_verification(
    photo_bytes: bytes,
    caption: str,
    order_id: int,
    user_telegram_id: int,
    grave_id: int,
) -> bool:
    """To'lov chekini BOT_TOKEN3 orqali adminlarga tasdiqlash tugmalari bilan yuboradi.

    Tugmalar bot tomonidagi `verify_payment_callback` ni ishga tushiradi —
    ya'ni web orqali kelgan chek ham xuddi botdagidek tasdiqlanadi.
    """
    if not PAYMENT_BOT_TOKEN or not ADMIN_IDS:
        logger.warning("PAYMENT_BOT_TOKEN yoki ADMIN_IDS sozlanmagan — chek yuborilmadi")
        return False

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Tasdiqlash",
             "callback_data": f"verify:true:{order_id}:{user_telegram_id}:{grave_id}"},
            {"text": "❌ Rad etish",
             "callback_data": f"verify:false:{order_id}:{user_telegram_id}:{grave_id}"},
        ]]
    }
    url = f"https://api.telegram.org/bot{PAYMENT_BOT_TOKEN}/sendPhoto"
    sent = False
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for admin_id in ADMIN_IDS:
                form = aiohttp.FormData()
                form.add_field("chat_id", str(admin_id))
                form.add_field("caption", caption)
                form.add_field("reply_markup", json.dumps(keyboard))
                form.add_field("photo", photo_bytes,
                               filename="receipt.jpg", content_type="image/jpeg")
                async with session.post(url, data=form) as resp:
                    if resp.status == 200:
                        sent = True
                    else:
                        logger.warning("sendPhoto failed for admin %s: %s %s",
                                       admin_id, resp.status, await resp.text())
    except Exception:  # noqa: BLE001
        logger.exception("send_receipt_for_verification failed for order %s", order_id)
    return sent

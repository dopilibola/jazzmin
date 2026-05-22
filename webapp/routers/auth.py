"""
Saytga kirish — ro'yxatdan o'tish FAQAT Telegram bot orqali.

Saytda:
  • Parol bilan kirish:  telefon + 6 xonali parol
  • Kod bilan kirish:    telefon -> botga kod keladi -> kod
  • Birinchi marta / parol tiklash: kod tasdiqlangach 6 xonali parol o'rnatiladi
"""
from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import RedirectResponse

from webapp.codes import generate_code, verify_code
from webapp.config import FRONT_URL
from webapp.db_extras import get_user_by_id, get_user_by_phone, update_user_profile
from webapp.deps import get_current_user, get_db, render, set_flash
from webapp.security import hash_password, verify_password
from webapp.telegram_send import send_code_to_telegram

router = APIRouter()


def _valid_pin(value: str) -> bool:
    """Parol kamida 6 ta raqamdan iborat bo'lishi kerak."""
    return value.isdigit() and len(value) >= 6


# -----------------------------------------------------------------------------
# Parol bilan kirish
# -----------------------------------------------------------------------------


@router.get("/login")
async def login_form(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html")


@router.post("/login")
async def login_submit(
    request: Request,
    phone: str = Form(""),
    password: str = Form(""),
    session=Depends(get_db),
):
    user = await get_user_by_phone(session, phone)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return render(request, "login.html",
                      {"errors": ["Telefon raqami yoki parol noto'g'ri."], "phone": phone})
    request.session["user_id"] = user.id
    set_flash(request, f"Xush kelibsiz, {user.full_name or 'foydalanuvchi'}!")
    return RedirectResponse("/", status_code=303)


# -----------------------------------------------------------------------------
# Kod so'rash (kod bilan kirish yoki parol tiklash)
# -----------------------------------------------------------------------------


@router.get("/code")
async def code_form(request: Request, reset: int = 0, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return render(request, "code_request.html", {"reset": bool(reset)})


@router.post("/code")
async def code_send(
    request: Request,
    phone: str = Form(""),
    reset: str = Form("0"),
    session=Depends(get_db),
):
    is_reset = reset == "1"
    user = await get_user_by_phone(session, phone)
    if not user:
        return render(request, "code_request.html", {
            "reset": is_reset, "phone": phone,
            "errors": ["Bu raqam topilmadi. Iltimos, avval Telegram bot orqali ro'yxatdan o'ting."],
        })
    if not user.telegram_id:
        return render(request, "code_request.html", {
            "reset": is_reset, "phone": phone,
            "errors": ["Bu hisob Telegram bilan bog'lanmagan. Telegram botdan foydalaning."],
        })

    code = generate_code(str(user.telegram_id))
    sent = await send_code_to_telegram(user.telegram_id, code)
    if not sent:
        return render(request, "code_request.html", {
            "reset": is_reset, "phone": phone,
            "errors": ["Kodni yuborib bo'lmadi. Botni ishga tushirganingizni (/start) tekshiring."],
        })

    request.session["pending_tg"] = user.telegram_id
    request.session["pending_user_id"] = user.id
    request.session["pending_reset"] = is_reset
    return RedirectResponse("/verify", status_code=303)


# -----------------------------------------------------------------------------
# Kodni tasdiqlash
# -----------------------------------------------------------------------------


@router.get("/verify")
async def verify_form(request: Request):
    if not request.session.get("pending_user_id"):
        return RedirectResponse("/login", status_code=303)
    return render(request, "verify.html")


@router.post("/verify")
async def verify_submit(request: Request, code: str = Form(""), session=Depends(get_db)):
    pending_tg = request.session.get("pending_tg")
    pending_uid = request.session.get("pending_user_id")
    if not pending_tg or not pending_uid:
        return RedirectResponse("/login", status_code=303)

    if not verify_code(str(pending_tg), code):
        return render(request, "verify.html",
                      {"errors": ["Kod noto'g'ri yoki muddati o'tgan."]})

    user = await get_user_by_id(session, pending_uid)
    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    is_reset = request.session.get("pending_reset")
    for key in ("pending_tg", "pending_user_id", "pending_reset"):
        request.session.pop(key, None)

    # Paroli bor + oddiy kod-login → to'g'ridan-to'g'ri kiritamiz
    if user.password_hash and not is_reset:
        request.session["user_id"] = user.id
        set_flash(request, "Xush kelibsiz!")
        return RedirectResponse("/", status_code=303)

    # Parol yo'q (birinchi marta) yoki tiklash → parol o'rnatish
    request.session["verified_user_id"] = user.id
    return RedirectResponse("/set-password", status_code=303)


# -----------------------------------------------------------------------------
# 6 xonali parol o'rnatish (birinchi marta yoki tiklash)
# -----------------------------------------------------------------------------


@router.get("/set-password")
async def set_password_form(request: Request):
    if not request.session.get("verified_user_id"):
        return RedirectResponse("/login", status_code=303)
    return render(request, "set_password.html")


@router.post("/set-password")
async def set_password_submit(
    request: Request,
    password: str = Form(""),
    password2: str = Form(""),
    session=Depends(get_db),
):
    uid = request.session.get("verified_user_id")
    if not uid:
        return RedirectResponse("/login", status_code=303)

    errors: list[str] = []
    if not _valid_pin(password):
        errors.append("Parol kamida 6 ta raqamdan iborat bo'lishi kerak.")
    if password != password2:
        errors.append("Parol tasdig'i mos kelmadi.")
    if errors:
        return render(request, "set_password.html", {"errors": errors})

    user = await get_user_by_id(session, uid)
    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    await update_user_profile(session, user, password_hash=hash_password(password))
    request.session.pop("verified_user_id", None)
    request.session["user_id"] = user.id
    set_flash(request, "Parol o'rnatildi. Xush kelibsiz!")
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    """Chiqish -> asl 'about' sahifasiga (front sayt domen ildizi)."""
    request.session.clear()
    return RedirectResponse(FRONT_URL, status_code=303)

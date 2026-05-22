"""Profil — ko'rish va tahrirlash."""
from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import RedirectResponse

from bot.database.queries import get_orders_by_user, list_user_graves
from webapp.db_extras import update_user_profile
from webapp.deps import get_current_user, get_db, render, set_flash
from webapp.security import normalize_phone

router = APIRouter()


@router.get("/profile")
async def profile_view(request: Request, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    graves = await list_user_graves(session, user.id)
    orders = await get_orders_by_user(session, user.id)
    return render(request, "profile.html",
                  {"user": user, "graves": graves, "orders": orders})


@router.get("/profile/edit")
async def profile_edit_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    return render(request, "profile_edit.html", {"user": user})


@router.post("/profile/edit")
async def profile_edit_submit(
    request: Request,
    full_name: str = Form(""),
    phone: str = Form(""),
    user=Depends(get_current_user),
    session=Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    full_name = full_name.strip()
    digits = normalize_phone(phone)
    errors: list[str] = []
    if len(full_name) < 3:
        errors.append("Ism-familiyangizni to'liq kiriting.")
    if len(digits) < 9:
        errors.append("Telefon raqamini to'g'ri kiriting.")
    if errors:
        return render(request, "profile_edit.html", {"user": user, "errors": errors})

    await update_user_profile(session, user, full_name=full_name, phone=digits)
    set_flash(request, "Profil yangilandi.")
    return RedirectResponse("/profile", status_code=303)

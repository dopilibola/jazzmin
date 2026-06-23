"""Xizmatlar — ro'yxat va buyurtma berish.

Xizmatlar Django admin panelidagi `catalog_service` jadvalidan o'qiladi —
bot ham aynan shu jadvaldan foydalanadi (yagona manba).
"""
from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import RedirectResponse

from bot.database.queries import (
    create_order_from_service,
    get_grave_by_id,
    list_user_graves,
    update_order_grave,
)
from webapp.catalog_models import get_catalog_service, get_catalog_services
from webapp.deps import get_current_user, get_db, render, set_flash

router = APIRouter()


@router.get("/services")
async def services_list(request: Request, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    services = await get_catalog_services(session)
    lang = user.language or "uz"
    items = [
        {
            "id": s.id,
            "name": s.get_name(lang),
            "description": s.get_description(lang),
            "price": int(s.price or 0),
        }
        for s in services
    ]
    return render(request, "services.html", {"user": user, "services": items})


@router.get("/services/{service_id}/order")
async def order_form(service_id: int, request: Request,
                     user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    service = await get_catalog_service(session, service_id)
    if not service:
        return RedirectResponse("/services", status_code=303)
    graves = await list_user_graves(session, user.id)
    lang = user.language or "uz"
    return render(request, "order_new.html", {
        "user": user,
        "graves": graves,
        "service": {"id": service.id, "name": service.get_name(lang),
                    "description": service.get_description(lang),
                    "price": int(service.price or 0)},
    })


@router.post("/services/{service_id}/order")
async def order_submit(
    service_id: int,
    request: Request,
    grave_id: str = Form(""),
    comment: str = Form(""),
    user=Depends(get_current_user),
    session=Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    service = await get_catalog_service(session, service_id)
    if not service:
        return RedirectResponse("/services", status_code=303)
    if not user.full_name or not user.phone_number:
        set_flash(request, "Buyurtma berish uchun avval profilingizni to'ldiring.", "error")
        return RedirectResponse("/profile/edit", status_code=303)

    grave = None
    if grave_id.isdigit():
        grave = await get_grave_by_id(session, int(grave_id), user.id)

    lang = user.language or "uz"
    order = await create_order_from_service(
        session, user.id, service.id, service.get_name(lang), int(service.price or 0),
        full_name=user.full_name,
        phone_number=user.phone_number,
        deceased_full_name=grave.deceased_full_name if grave else None,
        birth_year=grave.birth_year if grave else None,
        death_year=grave.death_year if grave else None,
        comment=(comment.strip() or None),
    )
    if grave:
        await update_order_grave(session, order.id, grave.id)
    return RedirectResponse(f"/payment/{order.id}", status_code=303)

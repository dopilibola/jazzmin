"""Buyurtmalar — ro'yxat, batafsil, va to'lov."""
import pathlib
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from starlette.responses import FileResponse, RedirectResponse, Response

from bot.database.queries import get_order_by_id, get_orders_by_user, update_order_receipt
from webapp.config import (
    BASE_DIR,
    PAYMENT_CARD_INTERNATIONAL,
    PAYMENT_CARD_INTERNAL,
    UPLOAD_DIR,
)
from webapp.deps import get_current_user, get_db, render, set_flash
from webapp.telegram_send import fetch_telegram_file, send_receipt_for_verification
from webapp.ui import format_price

router = APIRouter()


@router.get("/orders")
async def orders_list(request: Request, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    orders = await get_orders_by_user(session, user.id)
    return render(request, "orders.html", {"user": user, "orders": orders})


@router.get("/orders/{order_id}")
async def order_detail(order_id: int, request: Request,
                       user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    order = await get_order_by_id(session, order_id)
    if not order or order.user_id != user.id:
        return RedirectResponse("/orders", status_code=303)
    return render(request, "order_detail.html", {"user": user, "order": order})


@router.get("/orders/{order_id}/photo/{num}")
async def order_photo(order_id: int, num: int,
                      user=Depends(get_current_user), session=Depends(get_db)):
    """Buyurtmaning ish rasmini ko'rsatadi (Telegram'dan olib kelinadi)."""
    if not user:
        return Response(status_code=404)
    order = await get_order_by_id(session, order_id)
    if not order or order.user_id != user.id:
        return Response(status_code=404)
    file_id = order.photo1_file_id if num == 1 else (
        order.photo2_file_id if num == 2 else None)
    if not file_id:
        return Response(status_code=404)
    data = await fetch_telegram_file(file_id)
    if not data:
        return Response(status_code=404)
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


@router.get("/orders/{order_id}/receipt")
async def order_receipt(order_id: int, user=Depends(get_current_user),
                        session=Depends(get_db)):
    """To'lov chekini ko'rsatadi — web yuklama (lokal fayl) yoki Telegram file_id."""
    if not user:
        return Response(status_code=404)
    order = await get_order_by_id(session, order_id)
    if not order or order.user_id != user.id:
        return Response(status_code=404)
    rid = order.receipt_file_id
    if not rid:
        return Response(status_code=404)

    # Web-saytdan yuklangan chek — lokal fayl ("web:receipts/...")
    if rid.startswith("web:"):
        rel = rid[4:].lstrip("/")
        uploads = (BASE_DIR / "uploads").resolve()
        path = (uploads / rel).resolve()
        if not str(path).startswith(str(uploads)) or not path.is_file():
            return Response(status_code=404)
        return FileResponse(path)

    # Telegram orqali yuborilgan chek — file_id
    data = await fetch_telegram_file(rid)
    if not data:
        return Response(status_code=404)
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


@router.get("/payment/{order_id}")
async def payment_page(order_id: int, request: Request,
                       user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    order = await get_order_by_id(session, order_id)
    if not order or order.user_id != user.id:
        return RedirectResponse("/orders", status_code=303)
    return render(request, "payment.html", {
        "user": user, "order": order,
        "card_internal": PAYMENT_CARD_INTERNAL,
        "card_international": PAYMENT_CARD_INTERNATIONAL,
    })


@router.post("/payment/{order_id}")
async def payment_submit(
    order_id: int,
    request: Request,
    payment_method: str = Form("card"),
    receipt: UploadFile = File(None),
    user=Depends(get_current_user),
    session=Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    order = await get_order_by_id(session, order_id)
    if not order or order.user_id != user.id:
        return RedirectResponse("/orders", status_code=303)
    if not receipt or not receipt.filename:
        set_flash(request, "To'lov chekining rasmini yuklang.", "error")
        return RedirectResponse(f"/payment/{order_id}", status_code=303)

    ext = pathlib.Path(receipt.filename).suffix.lower() or ".jpg"
    fname = f"order{order_id}_{uuid.uuid4().hex[:8]}{ext}"
    content = await receipt.read()
    (UPLOAD_DIR / fname).write_bytes(content)
    await update_order_receipt(session, order_id, f"web:receipts/{fname}", payment_method)

    # Chekni Telegram orqali adminlarga tasdiqlashga yuboramiz (botdagidek)
    services = ", ".join(it.title for it in order.items) or "—"
    caption = (
        f"🧾 Yangi to'lov cheki — WEB\n\n"
        f"Buyurtma #{order_id}\n"
        f"👤 {order.full_name}\n"
        f"📞 {order.phone_number}\n"
        f"🛒 {services}\n"
        f"💰 {format_price(order.total_price)}"
    )
    user_tg = order.user.telegram_id if (order.user and order.user.telegram_id) else 0
    await send_receipt_for_verification(
        content, caption, order_id, user_tg, order.grave_id or 0
    )

    set_flash(request, "To'lov cheki qabul qilindi — admin tasdiqlashi kutilmoqda.")
    return RedirectResponse(f"/orders/{order_id}", status_code=303)

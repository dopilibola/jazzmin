"""
Admin handlers: upload photo reports to orders.
Admin IDs from .env (ADMIN_IDS).
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.db import async_session_factory
from bot.database.queries import add_order_photo, get_all_orders, get_order_by_id
from bot.states.forms import AdminPhotoState
from bot.utils.texts import get_status_label
from bot_config import ADMIN_IDS

router = Router(name="admin")


@router.message(Command("orders"))
async def admin_list_orders(message: Message) -> None:
    """Admin: /orders — list recent orders."""
    if message.from_user.id not in ADMIN_IDS:
        return
    async with async_session_factory() as session:
        orders = await get_all_orders(session, limit=15)
    if not orders:
        await message.answer("No orders yet.")
        return
    lines = []
    for o in orders:
        status = get_status_label("en", o.status)
        lines.append(f"#{o.id} — {o.user.full_name} — {status} — {o.total} sum")
    await message.answer("Recent orders:\n\n" + "\n".join(lines))

# FSM for photo upload: store order_id
# We use a simple dict in memory or FSM state
# For simplicity: admin sends /uploadphoto <order_id>, then sends photo(s)


@router.message(Command("uploadphoto"), F.text)
async def admin_upload_photo_start(message: Message, state: FSMContext) -> None:
    """Admin: /uploadphoto <order_id> — start photo upload for order."""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = (message.text or "").strip().split()
    if len(parts) < 2:
        await message.answer("Usage: /uploadphoto <order_id>")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("Invalid order ID. Use a number.")
        return
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await message.answer(f"Order #{order_id} not found.")
            return
    await state.update_data(admin_photo_order_id=order_id)
    await state.set_state(AdminPhotoState.waiting_photo)
    await message.answer(
        f"Send photo(s) for order #{order_id}. Send /done when finished."
    )


@router.message(AdminPhotoState.waiting_photo, F.photo, F.chat.type == "private")
async def admin_upload_photo_receive(message: Message, state: FSMContext) -> None:
    """Admin: receive photo and add to order."""
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    order_id = data.get("admin_photo_order_id")
    if order_id is None:
        return
    photo = message.photo[-1] if message.photo else None
    if not photo or not photo.file_id:
        return
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            await state.clear()
            await message.answer("Order not found.")
            return
        await add_order_photo(
            session,
            order_id,
            photo.file_id,
            photo_type="completed_report",
        )
        await session.commit()
    await message.answer(f"Photo added to order #{order_id}.")


@router.message(AdminPhotoState.waiting_photo, Command("done"), F.chat.type == "private")
async def admin_upload_photo_done(message: Message, state: FSMContext) -> None:
    """Admin: /done — finish photo upload."""
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    order_id = data.get("admin_photo_order_id")
    if order_id is not None:
        await state.clear()
        await message.answer(f"Photo upload finished for order #{order_id}.")


@router.message(Command("status"), F.text)
async def admin_update_status(message: Message) -> None:
    """Admin: /status <order_id> <pending|in_progress|completed|cancelled>"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = (message.text or "").strip().split()
    if len(parts) < 3:
        await message.answer("Usage: /status <order_id> <pending|in_progress|completed|cancelled>")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("Invalid order ID.")
        return
    status = parts[2].lower()
    if status not in ("pending", "in_progress", "completed", "cancelled"):
        await message.answer("Invalid status.")
        return
    from bot.database.queries import update_order_status

    async with async_session_factory() as session:
        order = await update_order_status(session, order_id, status)
        await session.commit()
    if order:
        await message.answer(f"Order #{order_id} status updated to {status}.")
    else:
        await message.answer("Order not found.")

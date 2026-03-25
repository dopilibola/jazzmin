"""
Complaint handler: User submits complaint with text + photos.
Sends to admin bot (BOT_TOKEN3) for review.
"""
import json
import logging
import socket
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.db import async_session_factory
from bot.database.queries import get_order_by_id
from bot.database.models import Complaint, COMPLAINT_STATUS_PENDING
from bot.states.forms import ComplaintState
from bot.utils.texts import get_text
from bot.keyboards.inline import feedback_inline
from bot_config import PAYMENT_BOT_TOKEN, BOT_TOKEN, ADMIN_IDS, TELEGRAM_GROUP

logger = logging.getLogger(__name__)

router = Router(name="complaint")


# -----------------------------------------------------------------------------
# Feedback callback - when user clicks "bad"
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("feedback:bad:"))
async def start_complaint_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """User clicked 'bad' - start complaint flow."""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    order_id = int(parts[2])

    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if not order:
            return

        worker_telegram_id = order.assigned_telegram_id or 0
        worker_username = order.assigned_username or "Ishchi"
        cemetery = order.grave.cemetery if order.grave else (order.cemetery.name if order.cemetery else "—")
        deceased = order.grave.deceased_full_name if order.grave else (order.deceased_full_name or "—")
        user_lang = order.user.language if order.user else "uz"
        photo1 = order.photo1_file_id
        photo2 = order.photo2_file_id

    # Save data to state
    await state.set_state(ComplaintState.waiting_text)
    await state.update_data(
        order_id=order_id,
        worker_telegram_id=worker_telegram_id,
        worker_username=worker_username,
        cemetery=cemetery,
        deceased=deceased,
        user_lang=user_lang,
        work_photo1=photo1,
        work_photo2=photo2,
        complaint_photos=[],
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n👎 Yomon"
    )

    # Ask for complaint reason
    await callback.message.answer(
        "😔 Xizmat yoqmaganiga uzr so'raymiz.\n\n"
        "📝 Iltimos, nima uchun mamnun bo'lmaganingizni yozing:"
    )


# -----------------------------------------------------------------------------
# Receive complaint text
# -----------------------------------------------------------------------------


@router.message(ComplaintState.waiting_text, F.text)
async def receive_complaint_text(message: Message, state: FSMContext) -> None:
    """Receive complaint reason text."""
    reason_text = (message.text or "").strip()

    if len(reason_text) < 5:
        await message.answer("Iltimos, sababni batafsilroq yozing (kamida 5 ta belgi).")
        return

    await state.update_data(reason=reason_text)
    await state.set_state(ComplaintState.waiting_photos)

    # Ask for photos
    done_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tayyor - Yuborish", callback_data="complaint:done")]
        ]
    )

    await message.answer(
        "📸 Endi rasm yuboring (ixtiyoriy).\n\n"
        "Bir nechta rasm yuborishingiz mumkin.\n"
        "Tayyor bo'lsangiz, pastdagi tugmani bosing:",
        reply_markup=done_button,
    )


# -----------------------------------------------------------------------------
# Receive complaint photos
# -----------------------------------------------------------------------------


@router.message(ComplaintState.waiting_photos, F.photo)
async def receive_complaint_photo(message: Message, state: FSMContext) -> None:
    """Receive complaint photos (multiple allowed)."""
    photo = message.photo[-1]
    file_id = photo.file_id

    data = await state.get_data()
    photos = data.get("complaint_photos", [])
    photos.append(file_id)
    await state.update_data(complaint_photos=photos)

    done_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Tayyor - Yuborish ({len(photos)} ta rasm)", callback_data="complaint:done")]
        ]
    )

    await message.answer(
        f"✅ Rasm qabul qilindi ({len(photos)} ta).\n"
        "Yana rasm yuborishingiz yoki tugmani bosishingiz mumkin:",
        reply_markup=done_button,
    )


# -----------------------------------------------------------------------------
# Complete complaint submission
# -----------------------------------------------------------------------------


@router.callback_query(ComplaintState.waiting_photos, lambda c: c.data == "complaint:done")
async def complete_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    """User finished submitting complaint - save and send to admin."""
    await callback.answer()

    data = await state.get_data()
    order_id = data.get("order_id")
    reason = data.get("reason", "")
    complaint_photos = data.get("complaint_photos", [])
    worker_telegram_id = data.get("worker_telegram_id", 0)
    worker_username = data.get("worker_username", "Ishchi")
    cemetery = data.get("cemetery", "—")
    deceased = data.get("deceased", "—")
    user_lang = data.get("user_lang", "uz")
    work_photo1 = data.get("work_photo1")
    work_photo2 = data.get("work_photo2")

    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name or "User"

    # Save to database
    async with async_session_factory() as session:
        order = await get_order_by_id(session, order_id)
        if order:
            # Update order
            order.feedback = "bad"
            order.feedback_reason = reason

        # Create complaint record
        complaint = Complaint(
            user_id=order.user_id if order else 0,
            order_id=order_id,
            reason=reason,
            photo_ids=json.dumps(complaint_photos) if complaint_photos else None,
            status=COMPLAINT_STATUS_PENDING,
        )
        session.add(complaint)
        await session.commit()
        complaint_id = complaint.id

    await state.clear()

    # Notify user
    await callback.message.edit_text(
        "✅ Shikoyatingiz qabul qilindi!\n\n"
        "Admin tez orada ko'rib chiqadi va javob beradi."
    )

    # Send to admin via BOT_TOKEN3
    if PAYMENT_BOT_TOKEN:
        try:
            await _send_complaint_to_admin(
                complaint_id=complaint_id,
                order_id=order_id,
                user_id=user_id,
                username=username,
                reason=reason,
                complaint_photos=complaint_photos,
                worker_telegram_id=worker_telegram_id,
                worker_username=worker_username,
                cemetery=cemetery,
                deceased=deceased,
                work_photo1=work_photo1,
                work_photo2=work_photo2,
            )
        except Exception as e:
            logger.error(f"Failed to send complaint to admin: {e}")


async def _send_complaint_to_admin(
    complaint_id: int,
    order_id: int,
    user_id: int,
    username: str,
    reason: str,
    complaint_photos: list[str],
    worker_telegram_id: int,
    worker_username: str,
    cemetery: str,
    deceased: str,
    work_photo1: str | None,
    work_photo2: str | None,
) -> None:
    """Send complaint with photos to admin bot (BOT_TOKEN3)."""
    from aiogram.types import BufferedInputFile

    # First, download all photos from main bot (file_ids are bot-specific)
    all_file_ids = []
    if work_photo1:
        all_file_ids.append(work_photo1)
    if work_photo2:
        all_file_ids.append(work_photo2)
    all_file_ids.extend(complaint_photos)

    photo_bytes_list = []
    if all_file_ids:
        main_session = AiohttpSession()
        main_session._connector_init["family"] = socket.AF_INET
        main_bot = Bot(
            token=BOT_TOKEN,
            session=main_session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            for file_id in all_file_ids[:10]:  # Max 10 photos
                try:
                    file = await main_bot.get_file(file_id)
                    content = await main_bot.download_file(file.file_path)
                    photo_bytes_list.append(content.read())
                except Exception as e:
                    logger.error(f"Failed to download photo {file_id}: {e}")
        finally:
            await main_bot.session.close()

    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    admin_bot = Bot(
        token=PAYMENT_BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        caption = (
            f"🚨 <b>YANGI SHIKOYAT</b> #{complaint_id}\n\n"
            f"📋 Buyurtma: #{order_id}\n"
            f"👤 Mijoz: @{username}\n"
            f"👷 Ishchi: @{worker_username}\n"
            f"🏛 Qabriston: {cemetery}\n"
            f"🪦 Marhum: {deceased}\n\n"
            f"📝 <b>Shikoyat sababi:</b>\n{reason}"
        )

        # Admin action buttons
        admin_buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Mijozga javob yozish",
                        callback_data=f"complaint:respond:{complaint_id}:{user_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔁 Qayta tozalashga yuborish",
                        callback_data=f"complaint:reclean:{complaint_id}:{order_id}:{worker_telegram_id}",
                    ),
                ],
            ]
        )

        for admin_id in ADMIN_IDS:
            try:
                if photo_bytes_list:
                    # Send photos as media group (re-upload as BufferedInputFile)
                    media = []
                    for i, photo_bytes in enumerate(photo_bytes_list):
                        if i == 0:
                            media.append(InputMediaPhoto(
                                media=BufferedInputFile(photo_bytes, filename=f"photo{i+1}.jpg"),
                                caption=caption
                            ))
                        else:
                            media.append(InputMediaPhoto(
                                media=BufferedInputFile(photo_bytes, filename=f"photo{i+1}.jpg")
                            ))
                    await admin_bot.send_media_group(chat_id=admin_id, media=media)
                else:
                    await admin_bot.send_message(chat_id=admin_id, text=caption)

                # Send action buttons
                await admin_bot.send_message(
                    chat_id=admin_id,
                    text="Nima qilasiz?",
                    reply_markup=admin_buttons,
                )
            except Exception as e:
                logger.error(f"Failed to send complaint to admin {admin_id}: {e}")
    finally:
        await admin_bot.session.close()

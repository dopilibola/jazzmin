"""
Work rating. User can rate completed orders: Like / Dislike + optional comment.
Flow: select order → view photos → Like/Dislike → optional comment.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import async_session_factory
from bot.database.queries import (
    create_rating,
    get_completed_orders_by_user,
    get_order_by_id,
    get_rating_for_order,
    get_user_by_telegram_id,
    update_rating_comment,
)
from bot.keyboards.inline import (
    orders_to_rate_inline,
    rating_like_dislike_inline,
    rating_skip_comment_inline,
)
from bot.keyboards.reply import main_menu_keyboard
from bot.states.forms import RatingCommentState
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.texts import get_text

router = Router(name="rating")

RATING_VALUES = ("like", "dislike")


async def _get_unrated_orders(session, user_id: int) -> list:
    """Get completed orders that user has not yet rated."""
    orders = await get_completed_orders_by_user(session, user_id)
    unrated = []
    for o in orders:
        existing = await get_rating_for_order(session, o.id)
        if not existing:
            unrated.append(o)
    return unrated


async def _get_lang(telegram_id: int) -> str:
    """Get user language from DB."""
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_rating"),
            get_text("ru", "btn_rating"),
            get_text("uz", "btn_rating"),
        ]
    )
)
async def show_rating_options(message: Message) -> None:
    """Show rating: select order to rate."""
    telegram_id = message.from_user.id
    lang = await _get_lang(telegram_id)
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await message.answer(
                get_text(lang, "no_orders_to_rate"),
                reply_markup=main_menu_keyboard(lang),
            )
            return
        orders = await _get_unrated_orders(session, user.id)
    if not orders:
        await message.answer(
            get_text(lang, "no_orders_to_rate"),
            reply_markup=main_menu_keyboard(lang),
        )
        return
    await message.answer(
        get_text(lang, "rating_select_order"),
        reply_markup=orders_to_rate_inline(orders, lang),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("rate_order:"))
async def select_order_to_rate(callback: CallbackQuery) -> None:
    """User selected an order. Show photos (if any) and Like/Dislike buttons."""
    await callback.answer()
    order_id = int(callback.data.split(":")[1])
    lang = await _get_lang(callback.from_user.id)
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            return
        order = await get_order_by_id(session, order_id)
        if not order or order.user_id != user.id or order.status != "completed":
            await callback.message.answer(
                get_text(lang, "no_orders_to_rate"),
                reply_markup=main_menu_keyboard(lang),
            )
            return
        existing = await get_rating_for_order(session, order_id)
        if existing:
            await safe_edit_text(callback, get_text(lang, "rating_already"))
            return

    # Send photos of completed work (if any)
    completed_photos = [p for p in order.photos if p.photo_type == "completed_report"]
    if completed_photos:
        from aiogram.types import InputMediaPhoto

        if len(completed_photos) == 1:
            await callback.message.answer_photo(
                completed_photos[0].file_id,
                caption=get_text(lang, "rating_photos_caption"),
            )
        else:
            media = [
                InputMediaPhoto(media=p.file_id) for p in completed_photos[:10]
            ]
            media[0].caption = get_text(lang, "rating_photos_caption")
            await callback.message.answer_media_group(media=media)
        await callback.message.answer(
            get_text(lang, "rating_prompt_like_dislike"),
            reply_markup=rating_like_dislike_inline(lang, order_id),
        )
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        # No photos: edit the list message to show rating prompt
        await safe_edit_text(
            callback,
            get_text(lang, "rating_prompt_like_dislike"),
            reply_markup=rating_like_dislike_inline(lang, order_id),
        )


@router.callback_query(lambda c: c.data and c.data.startswith("rate:"))
async def process_rating(callback: CallbackQuery, state: FSMContext) -> None:
    """Process Like/Dislike: rate:order_id:like or rate:order_id:dislike."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    order_id = int(parts[1])
    value = parts[2].lower()
    if value not in RATING_VALUES or order_id <= 0:
        return
    telegram_id = callback.from_user.id
    lang = await _get_lang(telegram_id)
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return
        order = await get_order_by_id(session, order_id)
        if not order or order.user_id != user.id:
            return
        existing = await get_rating_for_order(session, order_id)
        if existing:
            await safe_edit_text(callback, get_text(lang, "rating_already"))
            return
        rating = await create_rating(session, user.id, order_id, value)
        await session.commit()
        rating_id = rating.id

    await state.set_state(RatingCommentState.waiting_comment)
    await state.update_data(rating_id=rating_id)
    await safe_edit_text(
        callback,
        get_text(lang, "rating_comment_prompt"),
        reply_markup=rating_skip_comment_inline(lang),
    )


@router.message(RatingCommentState.waiting_comment, F.text)
async def process_rating_comment(message: Message, state) -> None:
    """Process optional comment or /skip."""
    text = (message.text or "").strip()
    if text.lower() in ("/skip", "skip"):
        lang = await _get_lang(message.from_user.id)
        await state.clear()
        await message.answer(
            get_text(lang, "rating_thanks"),
            reply_markup=main_menu_keyboard(lang),
        )
        return
    if not text:
        return
    data = await state.get_data()
    rating_id = data.get("rating_id")
    if not rating_id:
        await state.clear()
        return
    async with async_session_factory() as session:
        await update_rating_comment(session, rating_id, text[:2000])
        await session.commit()
    lang = await _get_lang(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text(lang, "rating_thanks"),
        reply_markup=main_menu_keyboard(lang),
    )


@router.callback_query(
    RatingCommentState.waiting_comment,
    F.data == "rating:skip",
)
async def skip_rating_comment(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip comment via inline button."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    await state.clear()
    await safe_edit_text(callback, get_text(lang, "rating_thanks"))
    await callback.message.answer(
        get_text(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang),
    )

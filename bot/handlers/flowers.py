"""
Flower feature module: categories, products, cart, checkout, payment.
Handles flower services for grave care application.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize

from bot.database.db import async_session_factory
from bot.database.queries import (
    add_flower_product_to_cart,
    clear_flower_cart,
    create_or_update_user,
    create_flower_order_from_cart,
    get_flower_cart_items,
    get_flower_category_by_id,
    get_flower_products_by_category,
    get_flower_product_by_id,
    get_all_flower_categories,
    get_order_by_id,
    get_user_by_telegram_id,
    remove_cart_item,
    update_order_receipt,
)
from bot.keyboards.inline import (
    flower_cart_inline,
    flower_categories_inline,
    flower_confirm_order_inline,
    flower_products_inline,
)
from bot.keyboards.reply import cancel_keyboard, main_menu_keyboard
from bot.states.forms import FlowerCheckoutState, FlowerPaymentState
from bot.utils.helpers import format_price
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_full_name, is_valid_year

router = Router(name="flowers")


async def _get_lang(telegram_id: int) -> str:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "ru"


# -----------------------------------------------------------------------------
# Flowers menu (categories)
# -----------------------------------------------------------------------------


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_flowers"),
            get_text("ru", "btn_flowers"),
            get_text("uz", "btn_flowers"),
        ]
    )
)
async def show_flower_menu(message: Message) -> None:
    """Show flower categories: planted around / placed on grave."""
    lang = await _get_lang(message.from_user.id)
    async with async_session_factory() as session:
        categories = await get_all_flower_categories(session)
    if not categories:
        await message.answer(
            get_text(lang, "flower_menu_title") + "\n\n" + get_text(lang, "cart_empty"),
            reply_markup=main_menu_keyboard(lang),
        )
        return
    text = get_text(lang, "flower_menu_title") + "\n\n"
    text += "1. " + categories[0].get_name(lang) + "\n"
    text += "2. " + categories[1].get_name(lang) if len(categories) > 1 else ""
    await message.answer(
        text,
        reply_markup=flower_categories_inline(categories, lang),
    )


# -----------------------------------------------------------------------------
# Continue Shopping (from add-to-cart notification)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data == "nav:continue:flowers")
async def continue_shopping_flowers_callback(callback: CallbackQuery) -> None:
    """
    Handle 'Continue Shopping' from add-to-cart notification.
    Edits the notification to show flower categories menu.
    """
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    async with async_session_factory() as session:
        categories = await get_all_flower_categories(session)
    if not categories:
        await safe_edit_text(
            callback,
            get_text(lang, "flower_menu_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    text = get_text(lang, "flower_menu_title") + "\n\n"
    text += "1. " + categories[0].get_name(lang) + "\n"
    if len(categories) > 1:
        text += "2. " + categories[1].get_name(lang)
    await safe_edit_text(
        callback,
        text,
        reply_markup=flower_categories_inline(categories, lang),
    )


# -----------------------------------------------------------------------------
# Category selected -> show products
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("flcat:"))
async def flower_category_callback(callback: CallbackQuery) -> None:
    """Handle category selection: show products or back to menu."""
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    back_to_services = data.endswith(":svc")
    data_clean = data.replace(":svc", "")

    if data_clean == "flcat:menu":
        async with async_session_factory() as session:
            categories = await get_all_flower_categories(session)
        text = get_text(lang, "flower_menu_title") + "\n\n"
        text += "1. " + categories[0].get_name(lang) + "\n"
        if len(categories) > 1:
            text += "2. " + categories[1].get_name(lang)
        await safe_edit_text(
            callback,
            text,
            reply_markup=flower_categories_inline(categories, lang, back_to_services),
        )
        return

    category_id = int(data_clean.replace("flcat:", ""))
    async with async_session_factory() as session:
        products = await get_flower_products_by_category(session, category_id)
    if not products:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return
    text = get_text(lang, "flower_catalog") + "\n\n"
    for p in products:
        text += f"• {p.get_name(lang)} — {format_price(p.price, lang)}\n"
        text += f"  {p.get_description(lang)[:60]}...\n\n"
    await safe_edit_text(
        callback,
        text,
        reply_markup=flower_products_inline(products, category_id, lang, back_to_services),
    )


# -----------------------------------------------------------------------------
# Add flower product to cart
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("flprod:add:"))
async def add_flower_product_callback(callback: CallbackQuery) -> None:
    """
    Add flower product to cart.
    - Updates cart in database (quantity, total)
    - Sends notification with product name, price
    - Shows Continue Shopping and View Cart buttons
    """
    await callback.answer()
    product_id = int(callback.data.replace("flprod:add:", ""))
    telegram_id = callback.from_user.id
    lang = await _get_lang(telegram_id)
    async with async_session_factory() as session:
        user = await create_or_update_user(session, telegram_id)
        await session.flush()
        product = await get_flower_product_by_id(session, product_id)
        if not product:
            await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
            return
        cart_item = await add_flower_product_to_cart(
            session,
            user.id,
            product_id,
            product.get_name(lang),
            product.price,
            1,
        )
        await session.commit()
    # Send notification with product details and action buttons
    from bot.services.cart_notifier import get_add_to_cart_message
    from bot.keyboards.inline import add_to_cart_notification_inline

    msg = get_add_to_cart_message(
        lang, product.get_name(lang), product.price, cart_item.quantity
    )
    await callback.message.answer(
        msg,
        reply_markup=add_to_cart_notification_inline(lang),
    )


# -----------------------------------------------------------------------------
# Flower cart: view, remove, clear, confirm
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("flcart:"))
async def flower_cart_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle flower cart: remove, clear, confirm order."""
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await safe_edit_text(callback, get_text(lang, "cart_empty"))
            return
        items = await get_flower_cart_items(session, user.id)

        if data.startswith("flcart:remove:"):
            item_id = int(data.replace("flcart:remove:", ""))
            await remove_cart_item(session, item_id, user.id)
            await session.commit()
            items = await get_flower_cart_items(session, user.id)
            if not items:
                await safe_edit_text(
                    callback,
                    get_text(lang, "cart_title") + "\n\n" + get_text(lang, "cart_empty"),
                )
                return
            content = _format_flower_cart(items, lang)
            await safe_edit_text(
                callback,
                get_text(lang, "cart_title") + "\n\n" + content,
                reply_markup=flower_cart_inline(lang, items, has_items=True),
            )
            return

        if data == "flcart:clear":
            await clear_flower_cart(session, user.id)
            await session.commit()
            await safe_edit_text(
                callback,
                get_text(lang, "cart_title") + "\n\n" + get_text(lang, "cart_empty"),
            )
            return

        if data == "flcart:confirm":
            await _start_flower_checkout_from_cart(callback, state)
            return


async def _start_flower_checkout_from_cart(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Start flower checkout (first_name, last_name, etc.) from cart."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
            return
        items = await get_flower_cart_items(session, user.id)
    if not items:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return
    await state.set_state(FlowerCheckoutState.first_name)
    await state.update_data(user_id=user.id)
    await safe_edit_text(callback, get_text(lang, "flower_order_first_name"))
    await callback.message.answer("👇", reply_markup=cancel_keyboard(lang))


def _format_flower_cart(items: list, lang: str) -> str:
    """Format flower cart for display."""
    lines = []
    for item in items:
        subtotal = item.quantity * item.price
        lines.append(f"• {item.title} x{item.quantity} — {format_price(subtotal, lang)}")
    total = sum(item.quantity * item.price for item in items)
    lines.append(f"\n<b>Total: {format_price(total, lang)}</b>")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Flower cart from main menu (show flower cart)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data == "flcart:view")
async def view_flower_cart_callback(callback: CallbackQuery) -> None:
    """View flower cart (triggered from somewhere)."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    telegram_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await create_or_update_user(session, telegram_id)
        await session.flush()
        items = await get_flower_cart_items(session, user.id)
    if not items:
        await safe_edit_text(
            callback,
            get_text(lang, "cart_title") + "\n\n" + get_text(lang, "cart_empty"),
        )
        return
    content = _format_flower_cart(items, lang)
    await safe_edit_text(
        callback,
        get_text(lang, "cart_title") + "\n\n" + content,
        reply_markup=flower_cart_inline(lang, items, has_items=True),
    )


# -----------------------------------------------------------------------------
# Flower checkout form (FSM): first name, last name, birth year, death year
# -----------------------------------------------------------------------------


@router.message(FlowerCheckoutState.first_name, F.text)
async def flower_checkout_first_name(message: Message, state: FSMContext) -> None:
    """Receive first name."""
    lang = await _get_lang(message.from_user.id)
    if (message.text or "").strip().lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(get_text(lang, "order_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return
    await state.update_data(first_name=(message.text or "").strip())
    await state.set_state(FlowerCheckoutState.last_name)
    await message.answer(get_text(lang, "flower_order_last_name"))


@router.message(FlowerCheckoutState.last_name, F.text)
async def flower_checkout_last_name(message: Message, state: FSMContext) -> None:
    """Receive last name."""
    lang = await _get_lang(message.from_user.id)
    if (message.text or "").strip().lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(get_text(lang, "order_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return
    await state.update_data(last_name=(message.text or "").strip())
    await state.set_state(FlowerCheckoutState.birth_year)
    await message.answer(get_text(lang, "flower_order_birth_year"))


@router.message(FlowerCheckoutState.birth_year, F.text)
async def flower_checkout_birth_year(message: Message, state: FSMContext) -> None:
    """Receive birth year."""
    lang = await _get_lang(message.from_user.id)
    if (message.text or "").strip().lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(get_text(lang, "order_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    if not is_valid_year(message.text or ""):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(birth_year=int((message.text or "").strip()))
    await state.set_state(FlowerCheckoutState.death_year)
    await message.answer(get_text(lang, "flower_order_death_year"))


@router.message(FlowerCheckoutState.death_year, F.text)
async def flower_checkout_death_year(message: Message, state: FSMContext) -> None:
    """Receive death year. Show summary and Proceed to Payment."""
    lang = await _get_lang(message.from_user.id)
    if (message.text or "").strip().lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(get_text(lang, "order_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    if not is_valid_year(message.text or ""):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(death_year=int((message.text or "").strip()))
    await state.set_state(FlowerCheckoutState.confirm)
    data = await state.get_data()
    async with async_session_factory() as session:
        items = await get_flower_cart_items(session, data["user_id"])
        total = sum(i.quantity * i.price for i in items)
    items_str = "\n".join(f"  • {i.title} x{i.quantity} — {format_price(i.quantity * i.price, lang)}" for i in items)
    total_str = format_price(total, lang)
    summary = get_text(lang, "flower_confirm_summary", items=items_str, total=total_str)
    await message.answer(
        summary,
        reply_markup=flower_confirm_order_inline(lang),
    )


# -----------------------------------------------------------------------------
# Proceed to Payment -> create order -> show payment instructions
# -----------------------------------------------------------------------------


@router.callback_query(
    FlowerCheckoutState.confirm,
    lambda c: c.data and c.data.startswith("flord:"),
)
async def flower_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Create order and show payment instructions (upload receipt)."""
    await callback.answer()
    data = callback.data
    lang = await _get_lang(callback.from_user.id)
    if data == "flord:cancel":
        await state.clear()
        await safe_edit_text(callback, get_text(lang, "order_cancelled"))
        await callback.message.answer(reply_markup=main_menu_keyboard(lang))
        return
    if data == "flord:proceed":
        form_data = await state.get_data()
        async with async_session_factory() as session:
            items = await get_flower_cart_items(session, form_data["user_id"])
            order = await create_flower_order_from_cart(
                session,
                form_data["user_id"],
                items,
                first_name=form_data.get("first_name", ""),
                last_name=form_data.get("last_name", ""),
                birth_year=form_data.get("birth_year"),
                death_year=form_data.get("death_year"),
            )
            await session.commit()
        await state.clear()
        if order:
            await state.update_data(flower_order_id=order.id)
            await state.set_state(FlowerPaymentState.upload_receipt)
            await safe_edit_text(
                callback,
                get_text(lang, "payment_upload_receipt"),
            )
        else:
            await safe_edit_text(callback, get_text(lang, "cart_empty"))
            await callback.message.answer(reply_markup=main_menu_keyboard(lang))


# -----------------------------------------------------------------------------
# Payment receipt upload
# -----------------------------------------------------------------------------


@router.message(FlowerPaymentState.upload_receipt, F.photo)
async def flower_receipt_upload(message: Message, state: FSMContext) -> None:
    """Accept receipt image, store file_id, attach to order, set status=payment_review."""
    data = await state.get_data()
    order_id = data.get("flower_order_id")
    if not order_id:
        await state.clear()
        return
    photo: PhotoSize = message.photo[-1]
    file_id = photo.file_id
    lang = await _get_lang(message.from_user.id)
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await state.clear()
            return
        order = await get_order_by_id(session, order_id)
        if not order or order.user_id != user.id:
            await message.answer(get_text(lang, "cart_empty"))
            await state.clear()
            return
        await update_order_receipt(session, order_id, file_id, "receipt_upload")
        await session.commit()
    await state.clear()
    await message.answer(
        get_text(lang, "payment_receipt_received"),
        reply_markup=main_menu_keyboard(lang),
    )

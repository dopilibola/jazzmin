"""
Flower feature module: flat product list, cart, checkout, payment.
All flower/product data + "Gul ekish" service come from Django Admin DB.
No intermediate category step — every flower is shown as a direct button.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize

from apps.botapp.helpers import (
    format_price,
    get_all_active_flower_products,
    get_flower_product_by_pk,
    get_flower_services,
    get_service_by_pk,
    get_user_language as _get_lang,
)
from bot.database.db import async_session_factory
from bot.database.queries import (
    add_flower_product_to_cart,
    add_flower_service_to_cart,
    clear_flower_cart,
    create_or_update_user,
    create_flower_order_from_cart,
    get_flower_cart_items,
    get_order_by_id,
    get_user_by_telegram_id,
    remove_cart_item,
    update_order_receipt,
)
from bot.keyboards.inline import (
    flower_cart_inline,
    flower_confirm_order_inline,
    flowers_direct_inline,
)
from bot.keyboards.reply import cancel_keyboard, main_menu_keyboard
from bot.states.forms import FlowerCheckoutState, FlowerPaymentState
from bot.utils.telegram_helpers import safe_edit_text
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_full_name, is_valid_year

router = Router(name="flowers")


# ---------------------------------------------------------------------------
# Helper: build flowers menu text + keyboard
# ---------------------------------------------------------------------------


async def _build_flowers_menu(lang: str):
    """Fetch all active flower products + flower services; return (text, keyboard)."""
    products = await get_all_active_flower_products()
    services = await get_flower_services()

    if not products and not services:
        return (
            get_text(lang, "flower_menu_title") + "\n\n" + get_text(lang, "cart_empty"),
            None,
        )

    lines = [get_text(lang, "flower_menu_title"), ""]
    for p in products:
        lines.append(f"🌸 {p.get_name(lang)} — {format_price(p.price, lang)}")
    for s in services:
        lines.append(f"🌱 {s.name} — {format_price(s.price, lang)}")

    text = "\n".join(lines)
    kb = flowers_direct_inline(products, services, lang)
    return text, kb


# ---------------------------------------------------------------------------
# Flowers menu (flat list — no categories)
# ---------------------------------------------------------------------------


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
    """Show ALL flower products + flower services as individual buttons."""
    lang = await _get_lang(message.from_user.id)
    text, kb = await _build_flowers_menu(lang)
    await message.answer(text, reply_markup=kb or main_menu_keyboard(lang))


# ---------------------------------------------------------------------------
# Continue Shopping (from add-to-cart notification)
# ---------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data == "nav:continue:flowers")
async def continue_shopping_flowers_callback(callback: CallbackQuery) -> None:
    """Handle 'Continue Shopping' — show flat flowers list."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    text, kb = await _build_flowers_menu(lang)
    await safe_edit_text(callback, text, reply_markup=kb)


# ---------------------------------------------------------------------------
# Add flower product to cart
# ---------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("flprod:add:"))
async def add_flower_product_callback(callback: CallbackQuery) -> None:
    """Add flower product to cart."""
    await callback.answer()
    product_id = int(callback.data.replace("flprod:add:", ""))
    telegram_id = callback.from_user.id
    lang = await _get_lang(telegram_id)

    product = await get_flower_product_by_pk(product_id)
    if not product:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return

    async with async_session_factory() as session:
        user = await create_or_update_user(session, telegram_id)
        await session.flush()
        cart_item = await add_flower_product_to_cart(
            session,
            user.id,
            product_id,
            product.get_name(lang),
            int(product.price),
            1,
        )
        await session.commit()

    from bot.keyboards.inline import add_to_cart_notification_inline
    from bot.services.cart_notifier import get_add_to_cart_message

    msg = get_add_to_cart_message(
        lang, product.get_name(lang), int(product.price), cart_item.quantity
    )
    await callback.message.answer(
        msg,
        reply_markup=add_to_cart_notification_inline(lang),
    )


# ---------------------------------------------------------------------------
# Add flower service (e.g. "Gul ekish") to cart
# ---------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("flsvc:add:"))
async def add_flower_service_callback(callback: CallbackQuery) -> None:
    """Add a flower-category service (e.g. Gul ekish) to the flower cart."""
    await callback.answer()
    service_id = int(callback.data.replace("flsvc:add:", ""))
    telegram_id = callback.from_user.id
    lang = await _get_lang(telegram_id)

    service = await get_service_by_pk(service_id)
    if not service:
        await callback.answer(get_text(lang, "cart_empty"), show_alert=True)
        return

    async with async_session_factory() as session:
        user = await create_or_update_user(session, telegram_id)
        await session.flush()
        cart_item = await add_flower_service_to_cart(
            session,
            user.id,
            service_id,
            service.name,
            int(service.price),
            1,
        )
        await session.commit()

    from bot.keyboards.inline import add_to_cart_notification_inline
    from bot.services.cart_notifier import get_add_to_cart_message

    msg = get_add_to_cart_message(
        lang, service.name, int(service.price), cart_item.quantity
    )
    await callback.message.answer(
        msg,
        reply_markup=add_to_cart_notification_inline(lang),
    )


# ---------------------------------------------------------------------------
# Flower cart: view, remove, clear, confirm
# ---------------------------------------------------------------------------


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

        if data == "flcart:view":
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


# ---------------------------------------------------------------------------
# Flower checkout form (FSM): first name, last name, birth year, death year
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Proceed to Payment -> create order -> show payment instructions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Payment receipt upload
# ---------------------------------------------------------------------------


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

"""
Inline keyboards (buttons under messages).
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.botapp.helpers import format_price
from bot.utils.texts import get_status_label, get_text


# -----------------------------------------------------------------------------
# Profile
# -----------------------------------------------------------------------------


def profile_inline(lang: str) -> InlineKeyboardMarkup:
    """Profile view: Update Profile + Change Language buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_update_profile"),
                    callback_data="profile:update",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_change_language"),
                    callback_data="profile:language",
                ),
            ],
        ]
    )


def grave_approximate_inline(lang: str, prefix: str) -> InlineKeyboardMarkup:
    """Aniq / Taxminan selection for birth or death date."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_exact"),
                    callback_data=f"grave:approx:{prefix}:0",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_approximate"),
                    callback_data=f"grave:approx:{prefix}:1",
                ),
            ],
        ]
    )


def relationship_inline(lang: str) -> InlineKeyboardMarkup:
    """Relationship status selection for grave (translated)."""
    # Relationship keys for translation
    relationships = [
        "grandmother", "grandfather", "mother", "father",
        "brother", "sister", "uncle", "aunt", "other"
    ]
    buttons = []
    row = []
    for rel in relationships:
        row.append(
            InlineKeyboardButton(
                text=get_text(lang, f"rel_{rel}"),
                callback_data=f"grave:rel:{rel}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [InlineKeyboardButton(text=get_text(lang, "btn_skip"), callback_data="grave:rel:skip")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grave_regions_inline(regions: list, lang: str) -> InlineKeyboardMarkup:
    """Region selection for adding grave."""
    buttons = [
        [InlineKeyboardButton(text=r.get_name(lang), callback_data=f"grave:region:{r.id}")]
        for r in regions
    ]
    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_cancel"), callback_data="grave:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grave_districts_inline(districts: list, lang: str) -> InlineKeyboardMarkup:
    """District selection for adding grave."""
    buttons = [
        [InlineKeyboardButton(text=d.get_name(lang), callback_data=f"grave:district:{d.id}")]
        for d in districts
    ]
    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="grave:back:district")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grave_cemeteries_inline(cemeteries: list, lang: str) -> InlineKeyboardMarkup:
    """Cemetery selection for adding grave."""
    buttons = [
        [InlineKeyboardButton(text=c.name, callback_data=f"grave:cemetery:{c.id}")]
        for c in cemeteries
    ]
    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="grave:back:cemetery")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def language_inline() -> InlineKeyboardMarkup:
    """Language selection: Uzbek, Russian, English."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            ],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        ]
    )


# -----------------------------------------------------------------------------
# Services (DB-based)
# -----------------------------------------------------------------------------


def services_main_inline(lang: str) -> InlineKeyboardMarkup:
    """Services section: Cleaning and Flowers buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_cleaning"),
                    callback_data="svc:cleaning",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_flowers"),
                    callback_data="svc:flowers",
                ),
            ],
        ]
    )


def services_list_inline(
    services: list, lang: str, add_back: bool = False
) -> InlineKeyboardMarkup:
    """List of services with Order (direct order, no cart). add_back=True adds Back to Services."""
    buttons = []
    for s in services:
        name = s.get_name(lang) if hasattr(s, 'get_name') else s.name
        buttons.append([
            InlineKeyboardButton(
                text=f"{name} — {format_price(s.price, lang)}",
                callback_data=f"svc:order:{s.id}",
            ),
        ])
    if add_back:
        buttons.append(
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="svc:main")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_inline(lang: str, service_id: int) -> InlineKeyboardMarkup:
    """Service detail: Add to Cart and Back."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_add_to_cart"),
                    callback_data=f"svc:add:{service_id}",
                ),
            ],
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="svc:list")],
        ]
    )


# -----------------------------------------------------------------------------
# Flowers — same pattern as Services (DB-based)
# -----------------------------------------------------------------------------


def flowers_list_inline(
    flowers: list, lang: str, add_back: bool = False
) -> InlineKeyboardMarkup:
    """List of flowers with Order (direct order, no cart). Same as services_list_inline."""
    buttons = []
    for f in flowers:
        # Icon based on plantable or not
        icon = "🌱" if getattr(f, 'is_plantable', False) else "💐"
        # Use total_price if available, otherwise price
        price = getattr(f, 'total_price', f.price)
        # Use localized name
        name = f.get_name(lang) if hasattr(f, 'get_name') else f.name
        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {name} — {format_price(price, lang)}",
                callback_data=f"fl:order:{f.id}",
            ),
        ])
    if add_back:
        buttons.append(
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="fl:main")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def flower_confirm_order_inline(lang: str) -> InlineKeyboardMarkup:
    """Proceed to Payment button after order form."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "flower_proceed_to_payment"),
                    callback_data="flord:proceed",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_cancel"),
                    callback_data="flord:cancel",
                ),
            ],
        ]
    )


def flower_cart_inline(lang: str, cart_items: list, has_items: bool) -> InlineKeyboardMarkup:
    """Flower cart: remove, clear, confirm order."""
    buttons = []
    for item in cart_items:
        label = (item.title[:30] + "…") if len(item.title) > 30 else item.title
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"❌ {label}",
                    callback_data=f"flcart:remove:{item.id}",
                ),
            ]
        )
    if has_items:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=get_text(lang, "cart_clear"),
                    callback_data="flcart:clear",
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=get_text(lang, "cart_place_order"),
                    callback_data="flcart:confirm",
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# -----------------------------------------------------------------------------
# Add to Cart notification (Continue Shopping, View Cart)
# -----------------------------------------------------------------------------


def add_to_cart_notification_inline(lang: str) -> InlineKeyboardMarkup:
    """
    Inline keyboard shown after adding flower to cart.
    Cart is flower-only. Continue Shopping -> flowers, View Cart -> flower cart.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_continue_shopping"),
                    callback_data="nav:continue:flowers",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_view_cart"),
                    callback_data="flcart:view",
                ),
            ],
        ]
    )


# -----------------------------------------------------------------------------
# Cart
# -----------------------------------------------------------------------------


def cart_inline(lang: str, cart_items: list, has_items: bool) -> InlineKeyboardMarkup:
    """Cart: remove per item, clear, checkout."""
    buttons = []
    for item in cart_items:
        label = (item.title[:30] + "…") if len(item.title) > 30 else item.title
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"❌ {label}",
                    callback_data=f"cart:remove:{item.id}",
                ),
            ]
        )
    if has_items:
        buttons.append(
            [InlineKeyboardButton(text=get_text(lang, "cart_clear"), callback_data="cart:clear")]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=get_text(lang, "cart_place_order"),
                    callback_data="cart:checkout",
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# -----------------------------------------------------------------------------
# Checkout (region, district, cemetery)
# -----------------------------------------------------------------------------


def order_regions_inline(regions: list, lang: str) -> InlineKeyboardMarkup:
    """Region selection."""
    buttons = [
        [InlineKeyboardButton(text=r.get_name(lang), callback_data=f"ord:region:{r.id}")]
        for r in regions
    ]
    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_cancel"), callback_data="ord:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_districts_inline(districts: list, lang: str) -> InlineKeyboardMarkup:
    """District selection."""
    buttons = [
        [InlineKeyboardButton(text=d.get_name(lang), callback_data=f"ord:district:{d.id}")]
        for d in districts
    ]
    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="ord:back:district")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_cemeteries_inline(cemeteries: list, lang: str) -> InlineKeyboardMarkup:
    """Cemetery selection."""
    buttons = [
        [InlineKeyboardButton(text=c.name, callback_data=f"ord:cemetery:{c.id}")]
        for c in cemeteries
    ]
    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="ord:back:cemetery")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_confirm_inline(lang: str) -> InlineKeyboardMarkup:
    """Confirm order and proceed to payment."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_confirm_order"),
                    callback_data="ord:confirm",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_cancel"),
                    callback_data="ord:cancel",
                ),
            ],
        ]
    )


# -----------------------------------------------------------------------------
# Payment
# -----------------------------------------------------------------------------


def payment_methods_inline(lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Two buttons: Internal card and Visa."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "payment_internal_btn"),
                    callback_data=f"pay:method:{order_id}:internal",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "payment_visa_btn"),
                    callback_data=f"pay:method:{order_id}:visa",
                ),
            ],
        ]
    )


def receipt_confirm_reject_inline(lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Confirm or Reject receipt (admin only)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "payment_confirm_btn"),
                    callback_data=f"pay:confirm:{order_id}",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "payment_reject_btn"),
                    callback_data=f"pay:reject:{order_id}",
                ),
            ],
        ]
    )


def receipt_verify_inline(order_id: int, user_telegram_id: int, grave_id: int = 0) -> InlineKeyboardMarkup:
    """True/False buttons for payment verification bot (BOT_TOKEN3)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ True",
                    callback_data=f"verify:true:{order_id}:{user_telegram_id}:{grave_id}",
                ),
                InlineKeyboardButton(
                    text="❌ False",
                    callback_data=f"verify:false:{order_id}:{user_telegram_id}:{grave_id}",
                ),
            ],
        ]
    )


def order_take_inline(order_id: int) -> InlineKeyboardMarkup:
    """Button to take an order (for workers in group)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📥 Buyurtma olindi",
                    callback_data=f"order:take:{order_id}",
                ),
            ],
        ]
    )


def photo_verify_inline(order_id: int, user_telegram_id: int, worker_telegram_id: int) -> InlineKeyboardMarkup:
    """True/False buttons for photo verification in BOT_TOKEN3."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ True - Tasdiqlash",
                    callback_data=f"photo:true:{order_id}:{user_telegram_id}:{worker_telegram_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ False - Rad etish",
                    callback_data=f"photo:false:{order_id}:{user_telegram_id}:{worker_telegram_id}",
                ),
            ],
        ]
    )


def order_retry_inline(order_id: int, worker_telegram_id: int) -> InlineKeyboardMarkup:
    """Cancel/Continue buttons for worker after rejection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Davom etish",
                    callback_data=f"retry:continue:{order_id}:{worker_telegram_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Buyurtmadan voz kechish",
                    callback_data=f"retry:cancel:{order_id}:{worker_telegram_id}",
                ),
            ],
        ]
    )


def feedback_inline(order_id: int, lang: str) -> InlineKeyboardMarkup:
    """Feedback buttons for customer after order completion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍 Yaxshi",
                    callback_data=f"feedback:good:{order_id}",
                ),
                InlineKeyboardButton(
                    text="👎 Yomon",
                    callback_data=f"feedback:bad:{order_id}",
                ),
            ],
        ]
    )


def select_grave_for_order_inline(graves: list, lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Select a grave for order, with Add New Grave as first option."""
    buttons = [
        [
            InlineKeyboardButton(
                text=get_text(lang, "btn_add_new_grave"),
                callback_data=f"pay:newgrave:{order_id}",
            ),
        ]
    ]
    for grave in graves:
        name = grave.deceased_full_name or "—"
        cemetery = grave.cemetery or "—"
        label = f"🪦 {name} ({cemetery})"
        if len(label) > 40:
            label = label[:37] + "..."
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"pay:grave:{order_id}:{grave.id}",
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# -----------------------------------------------------------------------------
# Order history
# -----------------------------------------------------------------------------


def order_list_inline(orders: list, lang: str) -> InlineKeyboardMarkup:
    """List of orders."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"#{o.id} — {get_status_label(lang, o.status)}",
                callback_data=f"order:detail:{o.id}",
            ),
        ]
        for o in orders
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_detail_inline(lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Order detail: back to list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="order:list")],
        ]
    )


# -----------------------------------------------------------------------------
# Rating
# -----------------------------------------------------------------------------


def orders_to_rate_inline(orders: list, lang: str) -> InlineKeyboardMarkup:
    """List of completed orders available to rate."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"#{o.id} — {get_status_label(lang, o.status)}",
                callback_data=f"rate_order:{o.id}",
            ),
        ]
        for o in orders
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def rating_like_dislike_inline(lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Like / Dislike buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "rating_like"),
                    callback_data=f"rate:{order_id}:like",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "rating_dislike"),
                    callback_data=f"rate:{order_id}:dislike",
                ),
            ],
        ]
    )


def rating_skip_comment_inline(lang: str) -> InlineKeyboardMarkup:
    """Skip comment button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "rating_skip_comment"),
                    callback_data="rating:skip",
                ),
            ],
        ]
    )


# -----------------------------------------------------------------------------
# User Submission
# -----------------------------------------------------------------------------


def submission_relationship_inline(lang: str) -> InlineKeyboardMarkup:
    """Relationship selection for user submission (translated)."""
    relationships = [
        "mother", "father", "grandmother", "grandfather",
        "spouse", "sibling", "child", "relative", "friend", "other"
    ]
    buttons = []
    row = []
    for rel in relationships:
        row.append(
            InlineKeyboardButton(
                text=get_text(lang, f"rel_{rel}"),
                callback_data=f"rel:{rel}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_inline(lang: str) -> InlineKeyboardMarkup:
    """Cancel button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_cancel"),
                    callback_data="submission:cancel",
                ),
            ],
        ]
    )



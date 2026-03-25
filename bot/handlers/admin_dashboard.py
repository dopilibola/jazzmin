"""
Admin Financial Dashboard Handler.
Provides financial overview, pricing control, and analytics.
"""
import logging
from decimal import Decimal
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services.finance import (
    get_financial_dashboard,
    get_worker_stats,
    get_all_services,
    get_all_cemeteries,
    create_service,
    update_service,
    create_cemetery,
    update_cemetery,
    set_pricing_rule,
    get_pricing_rules,
    format_money,
    DEFAULT_PLATFORM_PERCENT,
    DEFAULT_WORKER_PERCENT,
)
from bot_config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router(name="admin_dashboard")


# -----------------------------------------------------------------------------
# FSM States
# -----------------------------------------------------------------------------


class ServiceManageState(StatesGroup):
    """States for service management."""
    waiting_name = State()
    waiting_price = State()
    waiting_edit_name = State()
    waiting_edit_price = State()


class CemeteryManageState(StatesGroup):
    """States for cemetery management."""
    waiting_name = State()
    waiting_multiplier = State()
    waiting_edit_name = State()
    waiting_edit_multiplier = State()


class CommissionState(StatesGroup):
    """States for commission settings."""
    waiting_platform_percent = State()
    waiting_worker_percent = State()


class FilterState(StatesGroup):
    """States for dashboard filters."""
    selecting_filter = State()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMIN_IDS


def main_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main admin dashboard keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Dashboard", callback_data="fin:dashboard"),
            ],
            [
                InlineKeyboardButton(text="💰 Narxlar", callback_data="fin:pricing"),
                InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="fin:settings"),
            ],
            [
                InlineKeyboardButton(text="👷 Ishchilar", callback_data="fin:workers"),
                InlineKeyboardButton(text="📅 Filtrlash", callback_data="fin:filters"),
            ],
        ]
    )


def dashboard_period_keyboard() -> InlineKeyboardMarkup:
    """Dashboard period selection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 7 kun", callback_data="fin:dash:7"),
                InlineKeyboardButton(text="📈 30 kun", callback_data="fin:dash:30"),
            ],
            [
                InlineKeyboardButton(text="📉 90 kun", callback_data="fin:dash:90"),
                InlineKeyboardButton(text="📆 Barchasi", callback_data="fin:dash:365"),
            ],
            [
                InlineKeyboardButton(text="« Orqaga", callback_data="fin:main"),
            ],
        ]
    )


def pricing_menu_keyboard() -> InlineKeyboardMarkup:
    """Pricing management menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛠 Xizmatlar", callback_data="fin:services"),
            ],
            [
                InlineKeyboardButton(text="🪦 Qabristonlar", callback_data="fin:cemeteries"),
            ],
            [
                InlineKeyboardButton(text="💵 Komissiyalar", callback_data="fin:commissions"),
            ],
            [
                InlineKeyboardButton(text="« Orqaga", callback_data="fin:main"),
            ],
        ]
    )


def filter_menu_keyboard() -> InlineKeyboardMarkup:
    """Filter selection menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Sana bo'yicha", callback_data="fin:filter:date"),
            ],
            [
                InlineKeyboardButton(text="🪦 Qabriston bo'yicha", callback_data="fin:filter:cemetery"),
            ],
            [
                InlineKeyboardButton(text="🛠 Xizmat bo'yicha", callback_data="fin:filter:service"),
            ],
            [
                InlineKeyboardButton(text="🔄 Filtrni tozalash", callback_data="fin:filter:clear"),
            ],
            [
                InlineKeyboardButton(text="« Orqaga", callback_data="fin:main"),
            ],
        ]
    )


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Back to main menu button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Orqaga", callback_data="fin:main")],
        ]
    )


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------


@router.message(Command("moliya"))
async def cmd_finance(message: Message) -> None:
    """Handle /moliya command - admin financial dashboard."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return

    await message.answer(
        "💰 <b>MOLIYAVIY BOSHQARUV</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_dashboard_keyboard(),
    )


@router.message(F.text == "💰 Moliya")
async def btn_finance(message: Message) -> None:
    """Handle Moliya button."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu tugma faqat adminlar uchun.")
        return

    await message.answer(
        "💰 <b>MOLIYAVIY BOSHQARUV</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_dashboard_keyboard(),
    )


@router.callback_query(F.data == "fin:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main financial menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "💰 <b>MOLIYAVIY BOSHQARUV</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_dashboard_keyboard(),
    )


# -----------------------------------------------------------------------------
# Financial Dashboard
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:dashboard")
async def cb_dashboard_menu(callback: CallbackQuery) -> None:
    """Show dashboard period selection."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "📊 <b>MOLIYAVIY DASHBOARD</b>\n\n"
        "Davrni tanlang:",
        reply_markup=dashboard_period_keyboard(),
    )


@router.callback_query(F.data.startswith("fin:dash:"))
async def cb_show_dashboard(callback: CallbackQuery, state: FSMContext) -> None:
    """Show financial dashboard for selected period."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer("⏳ Yuklanmoqda...")

    days = int(callback.data.split(":")[2])

    # Get filters from state
    data = await state.get_data()
    cemetery_id = data.get("filter_cemetery_id")
    service_id = data.get("filter_service_id")

    dashboard = await get_financial_dashboard(
        days=days,
        cemetery_id=cemetery_id,
        service_id=service_id,
    )

    # Build dashboard text
    lines = [
        "━" * 20,
        "📊 <b>MOLIYAVIY DASHBOARD</b>",
        "━" * 20,
        "",
        f"📅 Davr: So'nggi <b>{days}</b> kun",
        "",
        f"💵 Umumiy daromad: <b>{format_money(dashboard['total_revenue'])}</b>",
        f"💰 Platform ulushi: <b>{format_money(dashboard['platform_revenue'])}</b>",
        f"👷 Ishchilarga: <b>{format_money(dashboard['worker_payouts'])}</b>",
        "",
        f"📦 Jami buyurtmalar: {dashboard['total_orders']}",
        f"✅ Bajarilgan: {dashboard['completed_orders']}",
        f"🔄 Qaytarilgan: {dashboard['returned_orders']}",
        f"❌ Bekor qilingan: {dashboard['canceled_orders']}",
        "",
        f"📈 Foyda foizi: <b>{dashboard['profit_margin']}%</b>",
        "",
    ]

    # Top workers
    if dashboard['top_workers']:
        lines.append("🏆 <b>Top Ishchilar:</b>")
        for i, w in enumerate(dashboard['top_workers'][:5], 1):
            lines.append(f"   {i}. @{w['username']} — {format_money(w['total'])} ({w['orders']} ta)")
        lines.append("")

    # Cemetery stats
    if dashboard['cemetery_stats']:
        lines.append("🪦 <b>Qabristonlar:</b>")
        for c in dashboard['cemetery_stats'][:5]:
            lines.append(f"   • {c['name']}: {format_money(c['total'])}")
        lines.append("")

    # Service stats
    if dashboard['service_stats']:
        lines.append("🛠 <b>Xizmatlar:</b>")
        for s in dashboard['service_stats'][:5]:
            lines.append(f"   • {s['name']}: {format_money(s['total'])}")
        lines.append("")

    lines.append("━" * 20)

    # Add filter info if any
    if cemetery_id or service_id:
        filter_info = "🔍 Filtr: "
        if cemetery_id:
            filter_info += f"Qabriston #{cemetery_id} "
        if service_id:
            filter_info += f"Xizmat #{service_id}"
        lines.insert(3, filter_info)
        lines.insert(4, "")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"fin:dash:{days}"),
                ],
                [
                    InlineKeyboardButton(text="📅 Boshqa davr", callback_data="fin:dashboard"),
                    InlineKeyboardButton(text="🔍 Filtrlash", callback_data="fin:filters"),
                ],
                [
                    InlineKeyboardButton(text="« Orqaga", callback_data="fin:main"),
                ],
            ]
        ),
    )


# -----------------------------------------------------------------------------
# Pricing Management
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:pricing")
async def cb_pricing_menu(callback: CallbackQuery) -> None:
    """Show pricing management menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "💰 <b>NARXLARNI BOSHQARISH</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=pricing_menu_keyboard(),
    )


# -----------------------------------------------------------------------------
# Services Management
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:services")
async def cb_services_list(callback: CallbackQuery) -> None:
    """Show services list."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    services = await get_all_services()

    if not services:
        text = "🛠 <b>XIZMATLAR</b>\n\nHozircha xizmatlar yo'q."
    else:
        lines = ["🛠 <b>XIZMATLAR RO'YXATI</b>", ""]
        for s in services:
            lines.append(f"• <b>{s.name}</b>")
            lines.append(f"  Narx: {format_money(s.base_price)}")
            lines.append(f"  ID: {s.id}")
            lines.append("")
        text = "\n".join(lines)

    # Build keyboard with services
    buttons = []
    for s in services[:10]:  # Limit to 10
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {s.name}",
                callback_data=f"fin:svc:edit:{s.id}",
            )
        ])

    buttons.append([InlineKeyboardButton(text="➕ Yangi xizmat", callback_data="fin:svc:add")])
    buttons.append([InlineKeyboardButton(text="« Orqaga", callback_data="fin:pricing")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "fin:svc:add")
async def cb_add_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding new service."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()
    await state.set_state(ServiceManageState.waiting_name)
    await callback.message.edit_text(
        "➕ <b>YANGI XIZMAT QO'SHISH</b>\n\n"
        "Xizmat nomini kiriting:",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(ServiceManageState.waiting_name)
async def receive_service_name(message: Message, state: FSMContext) -> None:
    """Receive new service name."""
    if not is_admin(message.from_user.id):
        return

    await state.update_data(service_name=message.text.strip())
    await state.set_state(ServiceManageState.waiting_price)
    await message.answer(
        f"✅ Xizmat nomi: <b>{message.text.strip()}</b>\n\n"
        "Endi bazaviy narxni kiriting (so'mda):",
    )


@router.message(ServiceManageState.waiting_price)
async def receive_service_price(message: Message, state: FSMContext) -> None:
    """Receive new service price and create."""
    if not is_admin(message.from_user.id):
        return

    try:
        price = Decimal(message.text.strip().replace(" ", "").replace(",", ""))
        if price < 0:
            raise ValueError("Negative price")
    except (ValueError, TypeError):
        await message.answer("❌ Noto'g'ri narx. Raqam kiriting:")
        return

    data = await state.get_data()
    service_name = data.get("service_name", "Unknown")

    service = await create_service(name=service_name, base_price=price)
    await state.clear()

    await message.answer(
        f"✅ <b>Xizmat yaratildi!</b>\n\n"
        f"📋 Nomi: {service.name}\n"
        f"💰 Narxi: {format_money(service.base_price)}\n"
        f"🆔 ID: {service.id}",
        reply_markup=back_to_main_keyboard(),
    )


@router.callback_query(F.data.startswith("fin:svc:edit:"))
async def cb_edit_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Edit service."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    service_id = int(callback.data.split(":")[3])
    await state.update_data(edit_service_id=service_id)
    await callback.answer()

    await callback.message.edit_text(
        "✏️ <b>XIZMATNI TAHRIRLASH</b>\n\n"
        "Nimani o'zgartirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📝 Nomini", callback_data=f"fin:svc:editname:{service_id}"),
                    InlineKeyboardButton(text="💰 Narxini", callback_data=f"fin:svc:editprice:{service_id}"),
                ],
                [
                    InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"fin:svc:delete:{service_id}"),
                ],
                [
                    InlineKeyboardButton(text="« Orqaga", callback_data="fin:services"),
                ],
            ]
        ),
    )


@router.callback_query(F.data.startswith("fin:svc:editprice:"))
async def cb_edit_service_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Edit service price."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    service_id = int(callback.data.split(":")[3])
    await state.update_data(edit_service_id=service_id)
    await state.set_state(ServiceManageState.waiting_edit_price)
    await callback.answer()

    await callback.message.edit_text(
        "💰 Yangi narxni kiriting (so'mda):",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(ServiceManageState.waiting_edit_price)
async def receive_edit_price(message: Message, state: FSMContext) -> None:
    """Receive edited service price."""
    if not is_admin(message.from_user.id):
        return

    try:
        price = Decimal(message.text.strip().replace(" ", "").replace(",", ""))
        if price < 0:
            raise ValueError("Negative price")
    except (ValueError, TypeError):
        await message.answer("❌ Noto'g'ri narx. Raqam kiriting:")
        return

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    service = await update_service(service_id, base_price=price)
    await state.clear()

    if service:
        await message.answer(
            f"✅ <b>Narx yangilandi!</b>\n\n"
            f"📋 {service.name}: {format_money(service.base_price)}",
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await message.answer("❌ Xizmat topilmadi", reply_markup=back_to_main_keyboard())


@router.callback_query(F.data.startswith("fin:svc:delete:"))
async def cb_delete_service(callback: CallbackQuery) -> None:
    """Delete (deactivate) service."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    service_id = int(callback.data.split(":")[3])
    service = await update_service(service_id, is_active=False)
    await callback.answer("✅ Xizmat o'chirildi" if service else "❌ Xizmat topilmadi", show_alert=True)
    await cb_services_list(callback)


# -----------------------------------------------------------------------------
# Cemeteries Management
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:cemeteries")
async def cb_cemeteries_list(callback: CallbackQuery) -> None:
    """Show cemeteries list."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    cemeteries = await get_all_cemeteries()

    if not cemeteries:
        text = "🪦 <b>QABRISTONLAR</b>\n\nHozircha qabristonlar yo'q."
    else:
        lines = ["🪦 <b>QABRISTONLAR RO'YXATI</b>", ""]
        for c in cemeteries[:15]:
            lines.append(f"• <b>{c.name}</b>")
            lines.append(f"  Koeffitsient: x{c.price_multiplier}")
            lines.append(f"  ID: {c.id}")
            lines.append("")
        text = "\n".join(lines)

    buttons = []
    for c in cemeteries[:8]:
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {c.name[:20]}",
                callback_data=f"fin:cem:edit:{c.id}",
            )
        ])

    buttons.append([InlineKeyboardButton(text="➕ Yangi qabriston", callback_data="fin:cem:add")])
    buttons.append([InlineKeyboardButton(text="« Orqaga", callback_data="fin:pricing")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "fin:cem:add")
async def cb_add_cemetery(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding new cemetery."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()
    await state.set_state(CemeteryManageState.waiting_name)
    await callback.message.edit_text(
        "➕ <b>YANGI QABRISTON QO'SHISH</b>\n\n"
        "Qabriston nomini kiriting:",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(CemeteryManageState.waiting_name)
async def receive_cemetery_name(message: Message, state: FSMContext) -> None:
    """Receive cemetery name."""
    if not is_admin(message.from_user.id):
        return

    await state.update_data(cemetery_name=message.text.strip())
    await state.set_state(CemeteryManageState.waiting_multiplier)
    await message.answer(
        f"✅ Qabriston nomi: <b>{message.text.strip()}</b>\n\n"
        "Narx koeffitsientini kiriting (masalan: 1.0, 1.2, 0.9):",
    )


@router.message(CemeteryManageState.waiting_multiplier)
async def receive_cemetery_multiplier(message: Message, state: FSMContext) -> None:
    """Receive cemetery multiplier and create."""
    if not is_admin(message.from_user.id):
        return

    try:
        multiplier = Decimal(message.text.strip().replace(",", "."))
        if multiplier <= 0:
            raise ValueError("Non-positive multiplier")
    except (ValueError, TypeError):
        await message.answer("❌ Noto'g'ri koeffitsient. Raqam kiriting (masalan: 1.2):")
        return

    data = await state.get_data()
    cemetery_name = data.get("cemetery_name", "Unknown")

    cemetery = await create_cemetery(name=cemetery_name, price_multiplier=multiplier)
    await state.clear()

    await message.answer(
        f"✅ <b>Qabriston yaratildi!</b>\n\n"
        f"🪦 Nomi: {cemetery.name}\n"
        f"📊 Koeffitsient: x{cemetery.price_multiplier}\n"
        f"🆔 ID: {cemetery.id}",
        reply_markup=back_to_main_keyboard(),
    )


@router.callback_query(F.data.startswith("fin:cem:edit:"))
async def cb_edit_cemetery(callback: CallbackQuery, state: FSMContext) -> None:
    """Edit cemetery."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    cemetery_id = int(callback.data.split(":")[3])
    await state.update_data(edit_cemetery_id=cemetery_id)
    await state.set_state(CemeteryManageState.waiting_edit_multiplier)
    await callback.answer()

    await callback.message.edit_text(
        "✏️ <b>QABRISTONNI TAHRIRLASH</b>\n\n"
        "Yangi narx koeffitsientini kiriting (masalan: 1.2):",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(CemeteryManageState.waiting_edit_multiplier)
async def receive_edit_multiplier(message: Message, state: FSMContext) -> None:
    """Receive edited cemetery multiplier."""
    if not is_admin(message.from_user.id):
        return

    try:
        multiplier = Decimal(message.text.strip().replace(",", "."))
        if multiplier <= 0:
            raise ValueError("Non-positive multiplier")
    except (ValueError, TypeError):
        await message.answer("❌ Noto'g'ri koeffitsient. Raqam kiriting:")
        return

    data = await state.get_data()
    cemetery_id = data.get("edit_cemetery_id")

    cemetery = await update_cemetery(cemetery_id, price_multiplier=multiplier)
    await state.clear()

    if cemetery:
        await message.answer(
            f"✅ <b>Koeffitsient yangilandi!</b>\n\n"
            f"🪦 {cemetery.name}: x{cemetery.price_multiplier}",
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await message.answer("❌ Qabriston topilmadi", reply_markup=back_to_main_keyboard())


# -----------------------------------------------------------------------------
# Commission Settings
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:commissions")
async def cb_commissions(callback: CallbackQuery) -> None:
    """Show commission settings."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    services = await get_all_services()
    rules = await get_pricing_rules()

    lines = [
        "💵 <b>KOMISSIYA SOZLAMALARI</b>",
        "",
        f"📊 Standart: Platform {DEFAULT_PLATFORM_PERCENT}% | Ishchi {DEFAULT_WORKER_PERCENT}%",
        "",
    ]

    if rules:
        lines.append("<b>Maxsus qoidalar:</b>")
        for r in rules[:10]:
            service_name = "?"
            for s in services:
                if s.id == r.service_id:
                    service_name = s.name
                    break
            cemetery_info = f" (Qabriston #{r.cemetery_id})" if r.cemetery_id else " (Barcha)"
            lines.append(f"• {service_name}{cemetery_info}")
            lines.append(f"  Platform: {r.platform_percent}% | Ishchi: {r.worker_percent}%")
            if r.custom_price:
                lines.append(f"  Maxsus narx: {format_money(r.custom_price)}")
            lines.append("")

    text = "\n".join(lines)

    buttons = []
    for s in services[:6]:
        buttons.append([
            InlineKeyboardButton(
                text=f"⚙️ {s.name}",
                callback_data=f"fin:comm:svc:{s.id}",
            )
        ])

    buttons.append([InlineKeyboardButton(text="« Orqaga", callback_data="fin:pricing")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("fin:comm:svc:"))
async def cb_commission_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Set commission for a service."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    service_id = int(callback.data.split(":")[3])
    await state.update_data(comm_service_id=service_id)
    await state.set_state(CommissionState.waiting_platform_percent)
    await callback.answer()

    await callback.message.edit_text(
        "💵 <b>KOMISSIYA SOZLASH</b>\n\n"
        "Platform ulushini kiriting (foizda, masalan: 30):",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(CommissionState.waiting_platform_percent)
async def receive_platform_percent(message: Message, state: FSMContext) -> None:
    """Receive platform commission percent."""
    if not is_admin(message.from_user.id):
        return

    try:
        percent = Decimal(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percent")
    except (ValueError, TypeError):
        await message.answer("❌ 0 dan 100 gacha raqam kiriting:")
        return

    await state.update_data(platform_percent=percent)
    await state.set_state(CommissionState.waiting_worker_percent)
    await message.answer(
        f"✅ Platform ulushi: {percent}%\n\n"
        "Endi ishchi ulushini kiriting (foizda):",
    )


@router.message(CommissionState.waiting_worker_percent)
async def receive_worker_percent(message: Message, state: FSMContext) -> None:
    """Receive worker commission percent and save."""
    if not is_admin(message.from_user.id):
        return

    try:
        percent = Decimal(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percent")
    except (ValueError, TypeError):
        await message.answer("❌ 0 dan 100 gacha raqam kiriting:")
        return

    data = await state.get_data()
    service_id = data.get("comm_service_id")
    platform_percent = data.get("platform_percent")

    rule = await set_pricing_rule(
        service_id=service_id,
        platform_percent=platform_percent,
        worker_percent=percent,
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Komissiya saqlandi!</b>\n\n"
        f"Platform: {rule.platform_percent}%\n"
        f"Ishchi: {rule.worker_percent}%",
        reply_markup=back_to_main_keyboard(),
    )


# -----------------------------------------------------------------------------
# Filters
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:filters")
async def cb_filters_menu(callback: CallbackQuery) -> None:
    """Show filter menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "🔍 <b>FILTRLASH</b>\n\n"
        "Dashboard uchun filtr tanlang:",
        reply_markup=filter_menu_keyboard(),
    )


@router.callback_query(F.data == "fin:filter:cemetery")
async def cb_filter_cemetery(callback: CallbackQuery, state: FSMContext) -> None:
    """Filter by cemetery."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    cemeteries = await get_all_cemeteries()
    buttons = []
    for c in cemeteries[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=c.name[:30],
                callback_data=f"fin:setfilter:cem:{c.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Orqaga", callback_data="fin:filters")])

    await callback.message.edit_text(
        "🪦 Qabristonni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("fin:setfilter:cem:"))
async def cb_set_cemetery_filter(callback: CallbackQuery, state: FSMContext) -> None:
    """Set cemetery filter."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    cemetery_id = int(callback.data.split(":")[3])
    await state.update_data(filter_cemetery_id=cemetery_id)
    await callback.answer("✅ Filtr qo'yildi", show_alert=True)
    await cb_dashboard_menu(callback)


@router.callback_query(F.data == "fin:filter:service")
async def cb_filter_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Filter by service."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    services = await get_all_services()
    buttons = []
    for s in services[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=s.name[:30],
                callback_data=f"fin:setfilter:svc:{s.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Orqaga", callback_data="fin:filters")])

    await callback.message.edit_text(
        "🛠 Xizmatni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("fin:setfilter:svc:"))
async def cb_set_service_filter(callback: CallbackQuery, state: FSMContext) -> None:
    """Set service filter."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    service_id = int(callback.data.split(":")[3])
    await state.update_data(filter_service_id=service_id)
    await callback.answer("✅ Filtr qo'yildi", show_alert=True)
    await cb_dashboard_menu(callback)


@router.callback_query(F.data == "fin:filter:clear")
async def cb_clear_filters(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear all filters."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await state.update_data(filter_cemetery_id=None, filter_service_id=None)
    await callback.answer("✅ Filtrlar tozalandi", show_alert=True)
    await cb_dashboard_menu(callback)


# -----------------------------------------------------------------------------
# Workers Analytics
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:workers")
async def cb_workers_list(callback: CallbackQuery) -> None:
    """Show workers list."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()

    # Get top workers from dashboard
    dashboard = await get_financial_dashboard(days=30)
    workers = dashboard.get("top_workers", [])

    if not workers:
        text = "👷 <b>ISHCHILAR</b>\n\nHozircha ma'lumot yo'q."
    else:
        lines = ["👷 <b>ISHCHILAR REYTINGI</b>", ""]
        for i, w in enumerate(workers, 1):
            lines.append(f"{i}. @{w['username']}")
            lines.append(f"   Daromad: {format_money(w['total'])}")
            lines.append(f"   Buyurtmalar: {w['orders']} ta")
            lines.append("")
        text = "\n".join(lines)

    buttons = []
    for w in workers[:8]:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 @{w['username']}",
                callback_data=f"fin:worker:{w['telegram_id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Orqaga", callback_data="fin:main")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("fin:worker:"))
async def cb_worker_details(callback: CallbackQuery) -> None:
    """Show worker details."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer("⏳ Yuklanmoqda...")

    worker_id = int(callback.data.split(":")[2])
    stats = await get_worker_stats(worker_id)

    if not stats.get("found"):
        await callback.message.edit_text(
            "❌ Ishchi topilmadi",
            reply_markup=back_to_main_keyboard(),
        )
        return

    lines = [
        "━" * 20,
        f"👷 <b>ISHCHI PROFILI</b>",
        "━" * 20,
        "",
        f"👤 @{stats['username'] or 'Unknown'}",
        f"🆔 ID: {stats['worker_telegram_id']}",
        "",
        f"💰 Jami daromad: <b>{format_money(stats['total_earned'])}</b>",
        "",
        f"📦 Jami buyurtmalar: {stats['total_orders']}",
        f"✅ Bajarilgan: {stats['completed_orders']}",
        f"🔄 Qaytarilgan: {stats['returned_orders']}",
        f"❌ Bekor qilingan: {stats['canceled_orders']}",
        "",
    ]

    if stats.get("by_service"):
        lines.append("🛠 <b>Xizmatlar bo'yicha:</b>")
        for s in stats["by_service"][:5]:
            lines.append(f"   • {s['name']}: {format_money(s['total'])} ({s['count']} ta)")
        lines.append("")

    if stats.get("by_cemetery"):
        lines.append("🪦 <b>Qabristonlar bo'yicha:</b>")
        for c in stats["by_cemetery"][:5]:
            lines.append(f"   • {c['name']}: {format_money(c['total'])} ({c['count']} ta)")
        lines.append("")

    if stats.get("last_order_at"):
        lines.append(f"📅 Oxirgi buyurtma: {stats['last_order_at'].strftime('%Y-%m-%d %H:%M')}")

    lines.append("━" * 20)

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="« Orqaga", callback_data="fin:workers")],
            ]
        ),
    )


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "fin:settings")
async def cb_settings(callback: CallbackQuery) -> None:
    """Show settings menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Faqat adminlar uchun", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "⚙️ <b>SOZLAMALAR</b>\n\n"
        f"📊 Standart platform ulushi: {DEFAULT_PLATFORM_PERCENT}%\n"
        f"👷 Standart ishchi ulushi: {DEFAULT_WORKER_PERCENT}%\n\n"
        "Bu qiymatlar kodda o'rnatilgan.\n"
        "Har bir xizmat uchun alohida komissiya 'Narxlar' bo'limidan sozlanadi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💵 Komissiyalar", callback_data="fin:commissions")],
                [InlineKeyboardButton(text="« Orqaga", callback_data="fin:main")],
            ]
        ),
    )

"""
Grave handlers: Add Grave (FSM), My Graves list.
"""
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

from bot.database.db import async_session_factory
from bot.database.queries import (
    add_grave,
    get_cemeteries_by_district,
    get_cemetery_by_id,
    get_district_by_id,
    get_districts_by_region,
    get_region_by_id,
    get_regions,
    get_user_by_telegram_id,
    list_user_graves,
)
from bot.keyboards.inline import (
    grave_cemeteries_inline,
    grave_districts_inline,
    grave_regions_inline,
    grave_approximate_inline,
    relationship_inline,
)
from bot.keyboards.reply import main_menu_keyboard, profile_menu_keyboard
from bot.states.forms import GraveState
from bot.utils.helpers import format_grave_date
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_month, is_valid_year
from apps.botapp.helpers import get_user_language as _get_lang

router = Router(name="graves")


async def _safe_callback_answer(callback: CallbackQuery) -> None:
    """Safely answer callback query, ignore if expired."""
    try:
        await _safe_callback_answer(callback)
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            logger.warning("Callback query expired: %s", callback.data)
        else:
            raise


async def _require_profile(telegram_id: int) -> tuple[bool, str | None]:
    """Check if user has complete profile. Returns (ok, lang)."""
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
    if not user or not user.full_name or not user.phone_number:
        return False, await _get_lang(telegram_id)
    return True, user.language


# -----------------------------------------------------------------------------
# Add Grave - button handler
# -----------------------------------------------------------------------------


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_add_grave"),
            get_text("ru", "btn_add_grave"),
            get_text("uz", "btn_add_grave"),
        ]
    )
)
async def start_add_grave(message: Message, state: FSMContext) -> None:
    """Start Add Grave flow: check profile, show regions."""
    await state.clear()
    telegram_id = message.from_user.id
    ok, lang = await _require_profile(telegram_id)
    if not ok:
        await message.answer(get_text(lang, "enter_full_name"))
        return
    async with async_session_factory() as session:
        regions = await get_regions(session)
    await state.set_state(GraveState.region)
    await state.update_data(lang=lang)
    await message.answer(
        get_text(lang, "grave_enter_region"),
        reply_markup=grave_regions_inline(regions, lang),
    )


# -----------------------------------------------------------------------------
# Add Grave - callbacks (region, district, cemetery, relationship)
# -----------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("grave:region:"))
async def cb_grave_region(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected region -> show districts."""
    await _safe_callback_answer(callback)
    region_id = int(callback.data.split(":")[-1])
    lang = (await state.get_data()).get("lang", "ru")
    async with async_session_factory() as session:
        region = await get_region_by_id(session, region_id)
        districts = await get_districts_by_region(session, region_id)
    if not region or not districts:
        await callback.message.answer(get_text(lang, "btn_cancel"))
        await state.clear()
        return
    await state.update_data(region_id=region_id, region_name=region.get_name(lang))
    await state.set_state(GraveState.district)
    await callback.message.answer(
        get_text(lang, "grave_enter_district"),
        reply_markup=grave_districts_inline(districts, lang),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("grave:district:"))
async def cb_grave_district(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected district -> show cemeteries."""
    await _safe_callback_answer(callback)
    district_id = int(callback.data.split(":")[-1])
    lang = (await state.get_data()).get("lang", "ru")
    async with async_session_factory() as session:
        district = await get_district_by_id(session, district_id)
        cemeteries = await get_cemeteries_by_district(session, district_id)
    if not district or not cemeteries:
        await callback.message.answer(get_text(lang, "btn_cancel"))
        await state.clear()
        return
    await state.update_data(
        district_id=district_id, district_name=district.get_name(lang)
    )
    await state.set_state(GraveState.cemetery)
    await callback.message.answer(
        get_text(lang, "grave_enter_cemetery"),
        reply_markup=grave_cemeteries_inline(cemeteries, lang),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("grave:cemetery:"))
async def cb_grave_cemetery(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected cemetery -> ask deceased name."""
    await _safe_callback_answer(callback)
    cemetery_id = int(callback.data.split(":")[-1])
    lang = (await state.get_data()).get("lang", "ru")
    async with async_session_factory() as session:
        cemetery = await get_cemetery_by_id(session, cemetery_id)
    if not cemetery:
        await callback.message.answer(get_text(lang, "btn_cancel"))
        await state.clear()
        return
    await state.update_data(cemetery_id=cemetery_id, cemetery_name=cemetery.name)
    await state.set_state(GraveState.deceased_full_name)
    await callback.message.answer(get_text(lang, "grave_enter_deceased"))


@router.callback_query(lambda c: c.data == "grave:back:district")
async def cb_grave_back_district(callback: CallbackQuery, state: FSMContext) -> None:
    """Back from district to region."""
    await _safe_callback_answer(callback)
    lang = (await state.get_data()).get("lang", "ru")
    async with async_session_factory() as session:
        regions = await get_regions(session)
    await state.set_state(GraveState.region)
    await state.update_data(region_id=None, region_name=None, district_id=None, district_name=None)
    await callback.message.answer(
        get_text(lang, "grave_enter_region"),
        reply_markup=grave_regions_inline(regions, lang),
    )


@router.callback_query(lambda c: c.data == "grave:back:cemetery")
async def cb_grave_back_cemetery(callback: CallbackQuery, state: FSMContext) -> None:
    """Back from cemetery to district."""
    await _safe_callback_answer(callback)
    data = await state.get_data()
    region_id = data.get("region_id")
    lang = data.get("lang", "ru")
    if not region_id:
        await state.clear()
        return
    async with async_session_factory() as session:
        districts = await get_districts_by_region(session, region_id)
    await state.set_state(GraveState.district)
    await state.update_data(cemetery_id=None, cemetery_name=None)
    await callback.message.answer(
        get_text(lang, "grave_enter_district"),
        reply_markup=grave_districts_inline(districts, lang),
    )


@router.callback_query(lambda c: c.data == "grave:cancel")
async def cb_grave_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel Add Grave flow."""
    await _safe_callback_answer(callback)
    lang = (await state.get_data()).get("lang", "ru")
    await state.clear()
    await callback.message.answer(
        get_text(lang, "grave_cancelled"),
        reply_markup=profile_menu_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# Add Grave - text handlers (deceased, birth_year, death_year)
# -----------------------------------------------------------------------------


@router.message(GraveState.deceased_full_name, F.text)
async def process_deceased(message: Message, state: FSMContext) -> None:
    """Process deceased name -> ask birth choice (Aniq/Taxminan)."""
    name = (message.text or "").strip()
    if len(name) < 2:
        lang = (await state.get_data()).get("lang", "ru")
        await message.answer(get_text(lang, "invalid_name"))
        return
    await state.update_data(deceased_full_name=name)
    await state.set_state(GraveState.birth_choice)
    lang = (await state.get_data()).get("lang", "ru")
    await message.answer(
        get_text(lang, "grave_enter_birth_choice"),
        reply_markup=grave_approximate_inline(lang, "birth"),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("grave:approx:birth:"))
async def cb_grave_birth_choice(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected Aniq or Taxminan for birth -> ask year (or year only)."""
    await _safe_callback_answer(callback)
    is_approx = callback.data.split(":")[-1] == "1"
    await state.update_data(birth_approximate=is_approx)
    lang = (await state.get_data()).get("lang", "ru")
    await state.set_state(GraveState.birth_year)
    msg = get_text(lang, "grave_enter_birth_year_only") if is_approx else get_text(lang, "grave_enter_birth_year")
    await callback.message.answer(msg)


@router.message(GraveState.birth_year, F.text)
async def process_birth_year(message: Message, state: FSMContext) -> None:
    """Process birth year. If Taxminan -> death. If Aniq -> ask month."""
    text = (message.text or "").strip()
    lang = (await state.get_data()).get("lang", "ru")
    if not is_valid_year(text):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(birth_year=int(text))
    data = await state.get_data()
    if data.get("birth_approximate"):
        await state.set_state(GraveState.death_choice)
        await message.answer(
            get_text(lang, "grave_enter_death_choice"),
            reply_markup=grave_approximate_inline(lang, "death"),
        )
    else:
        await state.set_state(GraveState.birth_month)
        await message.answer(get_text(lang, "grave_enter_birth_month"))


@router.message(GraveState.birth_month, F.text)
async def process_birth_month(message: Message, state: FSMContext) -> None:
    """Process birth month (Aniq) -> ask death choice."""
    text = (message.text or "").strip()
    lang = (await state.get_data()).get("lang", "ru")
    if not is_valid_month(text):
        await message.answer(get_text(lang, "grave_invalid_month"))
        return
    await state.update_data(birth_month=int(text))
    await state.set_state(GraveState.death_choice)
    await message.answer(
        get_text(lang, "grave_enter_death_choice"),
        reply_markup=grave_approximate_inline(lang, "death"),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("grave:approx:death:"))
async def cb_grave_death_choice(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected Aniq or Taxminan for death -> ask year (or year only)."""
    await _safe_callback_answer(callback)
    is_approx = callback.data.split(":")[-1] == "1"
    await state.update_data(death_approximate=is_approx)
    lang = (await state.get_data()).get("lang", "ru")
    await state.set_state(GraveState.death_year)
    msg = get_text(lang, "grave_enter_death_year_only") if is_approx else get_text(lang, "grave_enter_death_year")
    await callback.message.answer(msg)


@router.message(GraveState.death_year, F.text)
async def process_death_year(message: Message, state: FSMContext) -> None:
    """Process death year. If Taxminan -> relationship. If Aniq -> ask month."""
    text = (message.text or "").strip()
    lang = (await state.get_data()).get("lang", "ru")
    if not is_valid_year(text):
        await message.answer(get_text(lang, "order_invalid_year"))
        return
    await state.update_data(death_year=int(text))
    data = await state.get_data()
    if data.get("death_approximate"):
        await state.set_state(GraveState.relationship_status)
        await message.answer(
            get_text(lang, "grave_enter_relationship"),
            reply_markup=relationship_inline(lang),
        )
    else:
        await state.set_state(GraveState.death_month)
        await message.answer(get_text(lang, "grave_enter_death_month"))


@router.message(GraveState.death_month, F.text)
async def process_death_month(message: Message, state: FSMContext) -> None:
    """Process death month (Aniq) -> ask relationship."""
    text = (message.text or "").strip()
    lang = (await state.get_data()).get("lang", "ru")
    if not is_valid_month(text):
        await message.answer(get_text(lang, "grave_invalid_month"))
        return
    await state.update_data(death_month=int(text))
    await state.set_state(GraveState.relationship_status)
    await message.answer(
        get_text(lang, "grave_enter_relationship"),
        reply_markup=relationship_inline(lang),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("grave:rel:"))
async def cb_grave_relationship(callback: CallbackQuery, state: FSMContext) -> None:
    """User selected relationship -> save grave."""
    await _safe_callback_answer(callback)
    rel_part = callback.data.split(":")[-1]
    from bot.database.models import RELATIONSHIP_DEFAULT

    relationship = RELATIONSHIP_DEFAULT if rel_part == "skip" else rel_part
    data = await state.get_data()
    lang = data.get("lang", "ru")
    telegram_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await state.clear()
            await callback.message.answer(get_text(lang, "grave_cancelled"))
            return
        await add_grave(
            session,
            user.id,
            region=data.get("region_name", ""),
            district=data.get("district_name", ""),
            cemetery=data.get("cemetery_name", ""),
            deceased_full_name=data.get("deceased_full_name", ""),
            birth_year=data.get("birth_year"),
            birth_month=data.get("birth_month"),
            birth_approximate=data.get("birth_approximate", False),
            death_year=data.get("death_year"),
            death_month=data.get("death_month"),
            death_approximate=data.get("death_approximate", False),
            relationship_status=relationship,
        )
        await session.commit()
    await state.clear()
    await callback.message.answer(
        get_text(lang, "grave_added"),
        reply_markup=main_menu_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# My Graves - button handler
# -----------------------------------------------------------------------------


@router.message(
    F.text.in_(
        [
            get_text("en", "btn_my_graves"),
            get_text("ru", "btn_my_graves"),
            get_text("uz", "btn_my_graves"),
        ]
    )
)
async def show_my_graves(message: Message) -> None:
    """Show user's saved graves list."""
    telegram_id = message.from_user.id
    ok, lang = await _require_profile(telegram_id)
    if not ok:
        await message.answer(get_text(lang, "enter_full_name"))
        return
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        graves = await list_user_graves(session, user.id)
    if not graves:
        await message.answer(
            get_text(lang, "my_graves_empty"),
            reply_markup=profile_menu_keyboard(lang),
        )
        return
    text = get_text(lang, "my_graves_title") + "\n\n"
    for i, g in enumerate(graves, 1):
        birth = format_grave_date(
            g.birth_year, getattr(g, "birth_month", None),
            getattr(g, "birth_approximate", False), lang
        )
        death = format_grave_date(
            g.death_year, getattr(g, "death_month", None),
            getattr(g, "death_approximate", False), lang
        )
        text += get_text(
            lang,
            "profile_grave_item",
            num=i,
            name=g.deceased_full_name,
            relationship=g.relationship_status,
            cemetery=g.cemetery or "—",
            birth=birth,
            death=death,
        ) + "\n\n"
    await message.answer(
        text,
        reply_markup=profile_menu_keyboard(lang),
    )

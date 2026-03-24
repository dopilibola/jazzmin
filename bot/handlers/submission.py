"""
User Submission Flow Handler.
Collects: name, phone, relationship, 2 photos.
Sends data + photos to Telegram channel.
"""
import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from apps.botapp.helpers import get_user_language
from bot.keyboards.inline import submission_relationship_inline, cancel_inline
from bot.keyboards.reply import phone_keyboard, remove_keyboard, main_menu_keyboard
from bot.states.forms import UserSubmissionState
from bot.utils.texts import get_text
from bot.utils.validators import is_valid_full_name, is_valid_phone, normalize_phone
from bot_config import SUBMISSION_CHANNEL_ID

logger = logging.getLogger(__name__)
router = Router(name="submission")


def _get_nickname(message: Message) -> str:
    """Get user nickname: @username or first_name."""
    if message.from_user.username:
        return f"@{message.from_user.username}"
    return message.from_user.first_name or "User"


async def _get_lang(telegram_id: int) -> str:
    """Get user language."""
    return await get_user_language(telegram_id)


# -----------------------------------------------------------------------------
# Start Submission Flow (can be triggered from anywhere)
# -----------------------------------------------------------------------------


@router.message(Command("submit"))
async def cmd_submit(message: Message, state: FSMContext) -> None:
    """Handle /submit command to start submission flow."""
    await start_submission_flow(message, state)


async def start_submission_flow(message: Message, state: FSMContext) -> None:
    """Start the user submission flow."""
    lang = await _get_lang(message.from_user.id)
    nickname = _get_nickname(message)

    await state.clear()
    await state.set_state(UserSubmissionState.full_name)
    await state.update_data(lang=lang, nickname=nickname)

    # Welcome with nickname
    await message.answer(get_text(lang, "submission_welcome", nickname=nickname))
    await message.answer(get_text(lang, "submission_enter_name"))


# -----------------------------------------------------------------------------
# Step 1: Full Name
# -----------------------------------------------------------------------------


@router.message(UserSubmissionState.full_name, F.text)
async def process_submission_name(message: Message, state: FSMContext) -> None:
    """Process full name input."""
    data = await state.get_data()
    lang = data.get("lang", "uz")

    if not is_valid_full_name(message.text or ""):
        await message.answer(get_text(lang, "invalid_name"))
        return

    full_name = (message.text or "").strip()
    await state.update_data(full_name=full_name)
    await state.set_state(UserSubmissionState.phone)

    await message.answer(
        get_text(lang, "submission_enter_phone"),
        reply_markup=phone_keyboard(lang),
    )


# -----------------------------------------------------------------------------
# Step 2: Phone Number
# -----------------------------------------------------------------------------


@router.message(UserSubmissionState.phone, F.contact)
async def process_submission_phone_contact(message: Message, state: FSMContext) -> None:
    """Process phone from shared Telegram contact."""
    contact = message.contact
    if not contact or not contact.phone_number:
        return

    phone = (contact.phone_number or "").strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    await _proceed_to_relationship(message, state, phone)


@router.message(UserSubmissionState.phone, F.text)
async def process_submission_phone_text(message: Message, state: FSMContext) -> None:
    """Process phone from typed text."""
    data = await state.get_data()
    lang = data.get("lang", "uz")

    phone = (message.text or "").strip()
    if not is_valid_phone(phone):
        await message.answer(get_text(lang, "invalid_phone"))
        return

    phone = normalize_phone(phone)
    if not phone.startswith("+"):
        phone = "+" + phone

    await _proceed_to_relationship(message, state, phone)


async def _proceed_to_relationship(message: Message, state: FSMContext, phone: str) -> None:
    """Save phone and move to relationship selection."""
    data = await state.get_data()
    lang = data.get("lang", "uz")

    await state.update_data(phone=phone)
    await state.set_state(UserSubmissionState.relationship)

    await message.answer(
        get_text(lang, "submission_select_relationship"),
        reply_markup=submission_relationship_inline(lang),
    )


# -----------------------------------------------------------------------------
# Step 3: Relationship Selection
# -----------------------------------------------------------------------------


@router.callback_query(UserSubmissionState.relationship, F.data.startswith("rel:"))
async def process_submission_relationship(callback: CallbackQuery, state: FSMContext) -> None:
    """Process relationship selection."""
    await callback.answer()

    rel_key = callback.data.split(":")[1]  # e.g., "mother", "father"
    data = await state.get_data()
    lang = data.get("lang", "uz")

    # Get localized relationship name
    relationship = get_text(lang, f"rel_{rel_key}")

    await state.update_data(relationship=relationship, relationship_key=rel_key)
    await state.set_state(UserSubmissionState.photo_1)

    await callback.message.edit_text(
        f"✅ {relationship}\n\n" + get_text(lang, "submission_send_photo_1")
    )


# -----------------------------------------------------------------------------
# Step 4: First Photo
# -----------------------------------------------------------------------------


@router.message(UserSubmissionState.photo_1, F.photo)
async def process_submission_photo_1(message: Message, state: FSMContext) -> None:
    """Process first photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")

    # Get the largest photo
    photo = message.photo[-1]
    photo_1_id = photo.file_id

    await state.update_data(photo_1_id=photo_1_id)
    await state.set_state(UserSubmissionState.photo_2)

    await message.answer(get_text(lang, "submission_send_photo_2"))


@router.message(UserSubmissionState.photo_1, F.text)
async def process_submission_photo_1_text_error(message: Message, state: FSMContext) -> None:
    """Handle text when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_error"))


@router.message(UserSubmissionState.photo_1, F.document)
async def process_submission_photo_1_doc_error(message: Message, state: FSMContext) -> None:
    """Handle document when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_file_error"))


@router.message(UserSubmissionState.photo_1, F.sticker)
async def process_submission_photo_1_sticker_error(message: Message, state: FSMContext) -> None:
    """Handle sticker when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_error"))


@router.message(UserSubmissionState.photo_1)
async def process_submission_photo_1_any_error(message: Message, state: FSMContext) -> None:
    """Handle any other content when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_error"))


# -----------------------------------------------------------------------------
# Step 5: Second Photo
# -----------------------------------------------------------------------------


@router.message(UserSubmissionState.photo_2, F.photo)
async def process_submission_photo_2(message: Message, state: FSMContext) -> None:
    """Process second photo and complete submission."""
    data = await state.get_data()
    lang = data.get("lang", "uz")

    # Get the largest photo
    photo = message.photo[-1]
    photo_2_id = photo.file_id

    # Get all collected data
    full_name = data.get("full_name", "")
    phone = data.get("phone", "")
    relationship = data.get("relationship", "")
    photo_1_id = data.get("photo_1_id", "")
    nickname = data.get("nickname", "")

    # Format username for display
    username = nickname if nickname.startswith("@") else f"—"

    # Clear state
    await state.clear()

    # Send success message to user
    await message.answer(get_text(lang, "submission_success"))

    # Show main menu
    await message.answer(
        get_text(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang),
    )

    # Send to channel if configured
    if SUBMISSION_CHANNEL_ID:
        try:
            channel_id = int(SUBMISSION_CHANNEL_ID)

            # Send caption with user info
            caption = get_text(
                lang,
                "submission_channel_caption",
                name=full_name,
                username=username,
                phone=phone,
                relationship=relationship,
            )

            # Send first photo with caption
            await message.bot.send_photo(
                chat_id=channel_id,
                photo=photo_1_id,
                caption=caption,
            )

            # Send second photo
            await message.bot.send_photo(
                chat_id=channel_id,
                photo=photo_2_id,
                caption=f"📸 Photo 2 - {full_name}",
            )

            logger.info(f"Submission sent to channel: user={message.from_user.id}, name={full_name}")

        except Exception as e:
            logger.error(f"Failed to send submission to channel: {e}")


@router.message(UserSubmissionState.photo_2, F.text)
async def process_submission_photo_2_text_error(message: Message, state: FSMContext) -> None:
    """Handle text when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_error"))


@router.message(UserSubmissionState.photo_2, F.document)
async def process_submission_photo_2_doc_error(message: Message, state: FSMContext) -> None:
    """Handle document when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_file_error"))


@router.message(UserSubmissionState.photo_2, F.sticker)
async def process_submission_photo_2_sticker_error(message: Message, state: FSMContext) -> None:
    """Handle sticker when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_error"))


@router.message(UserSubmissionState.photo_2)
async def process_submission_photo_2_any_error(message: Message, state: FSMContext) -> None:
    """Handle any other content when expecting photo."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await message.answer(get_text(lang, "submission_photo_error"))


# -----------------------------------------------------------------------------
# Cancel handler
# -----------------------------------------------------------------------------


@router.callback_query(F.data == "submission:cancel")
async def cancel_submission(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel submission flow."""
    await callback.answer()
    lang = await _get_lang(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(get_text(lang, "grave_cancelled"))
    await callback.message.answer(
        get_text(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang),
    )

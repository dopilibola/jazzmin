"""
Reply keyboards (buttons under input).
Main menu: Services, Profile, Support, About.
Sub-menus: only sub-buttons + Back (no parent button repeated).
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.utils.texts import get_text


def main_menu_keyboard(lang: str = "ru", is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Main menu: Services, Profile, Support, About. Admin has Analytics."""
    keyboard = [
        [
            KeyboardButton(text=get_text(lang, "btn_services")),
            # KeyboardButton(text=get_text(lang, "btn_flowers")),  # COMMENTED OUT
        ],
        [
            KeyboardButton(text=get_text(lang, "btn_profile")),
            KeyboardButton(text=get_text(lang, "btn_about")),
        ],
        [
            KeyboardButton(text=get_text(lang, "btn_support")),
        ],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="📊 Analiz")])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def back_to_main_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Simple keyboard with only Back to Main Menu button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_main_menu"))],
        ],
        resize_keyboard=True,
    )


def start_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Alias for main menu."""
    return main_menu_keyboard(lang)


def profile_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Profile menu: Add Grave, My Graves, Change Language, Back to main."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_text(lang, "btn_add_grave")),
                KeyboardButton(text=get_text(lang, "btn_my_graves")),
            ],
            [
                KeyboardButton(text=get_text(lang, "btn_change_language")),
            ],
            [
                KeyboardButton(text=get_text(lang, "btn_main_menu")),
            ],
        ],
        resize_keyboard=True,
    )


def phone_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Request phone number via Telegram contact button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_share_phone"), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Cancel button for FSM flows."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_cancel"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove reply keyboard."""
    return ReplyKeyboardRemove()

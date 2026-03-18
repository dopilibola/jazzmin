"""
Reply keyboards (buttons under input).
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.utils.texts import get_text


def main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Main menu: Services, Flowers | Profile, Support | About. Cart only inside Flowers."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_text(lang, "btn_services")),
                KeyboardButton(text=get_text(lang, "btn_flowers")),
            ],
            [
                KeyboardButton(text=get_text(lang, "btn_profile")),
                KeyboardButton(text=get_text(lang, "btn_support")),
            ],
            [
                KeyboardButton(text=get_text(lang, "btn_about")),
            ],
        ],
        resize_keyboard=True,
    )


def profile_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Profile menu: Add Grave, My Graves, Back to main (no redundant Profile button)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_text(lang, "btn_add_grave")),
                KeyboardButton(text=get_text(lang, "btn_my_graves")),
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

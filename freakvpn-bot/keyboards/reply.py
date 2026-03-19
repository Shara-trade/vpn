"""
Reply-клавиатуры для пользователя.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils.constants import (
    BTN_MY_KEY, BTN_PROFILE, BTN_BUY, BTN_SUPPORT
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает главное меню пользователя."""
    keyboard = [
        [KeyboardButton(text=BTN_MY_KEY), KeyboardButton(text=BTN_PROFILE)],
        [KeyboardButton(text=BTN_BUY), KeyboardButton(text=BTN_SUPPORT)]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает меню администратора."""
    from utils.constants import (
        BTN_ADMIN_USERS, BTN_ADMIN_BALANCE, BTN_ADMIN_STATS,
        BTN_ADMIN_SERVERS, BTN_ADMIN_MAILING, BTN_ADMIN_SETTINGS
    )
    
    keyboard = [
        [KeyboardButton(text=BTN_ADMIN_USERS), KeyboardButton(text=BTN_ADMIN_BALANCE)],
        [KeyboardButton(text=BTN_ADMIN_STATS), KeyboardButton(text=BTN_ADMIN_SERVERS)],
        [KeyboardButton(text=BTN_ADMIN_MAILING), KeyboardButton(text=BTN_ADMIN_SETTINGS)]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

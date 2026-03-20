"""
Reply-клавиатуры для пользователя и администратора.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главная клавиатура пользователя.
    
    Returns:
        ReplyKeyboardMarkup с 4 кнопками
    """
    keyboard = [
        [
            KeyboardButton(text="🔌 Мой ключ"),
            KeyboardButton(text="📊 Профиль"),
        ],
        [
            KeyboardButton(text="💰 Купить / Продлить"),
            KeyboardButton(text="🆘 Поддержка"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура администратора.
    
    Returns:
        ReplyKeyboardMarkup с кнопками админ-панели
    """
    keyboard = [
        [
            KeyboardButton(text="👥 Пользователи"),
            KeyboardButton(text="💰 Пополнить баланс"),
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="🌍 Серверы"),
        ],
        [
            KeyboardButton(text="✉️ Рассылка"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены.
    
    Returns:
        ReplyKeyboardMarkup с кнопкой отмены
    """
    keyboard = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

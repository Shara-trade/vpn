"""
Reply-клавиатуры для пользователя и администратора.
Все кнопки без эмодзи (кроме Отмена - с эмодзи по ТЗ).
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главная клавиатура пользователя (StarinaVPN).
    Все кнопки без эмодзи.
    
    Returns:
        ReplyKeyboardMarkup с 7 кнопками
    """
    keyboard = [
        [KeyboardButton(text="Купить")],
        [KeyboardButton(text="Мои ключи"), KeyboardButton(text="Профиль")],
        [KeyboardButton(text="Поддержка"), KeyboardButton(text="Отзывы")],
        [KeyboardButton(text="Промокод"), KeyboardButton(text="Статус серверов")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура администратора (FreakVPN).
    С эмодзи для удобства.
    
    Returns:
        ReplyKeyboardMarkup с кнопками админ-панели
    """
    keyboard = [
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🌍 Серверы"), KeyboardButton(text="⚙️ Прочее")],
        [KeyboardButton(text="📋 Логи"), KeyboardButton(text="🎫 Промокоды")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="📨 Рассылка")],
        [KeyboardButton(text="❌ Закрыть")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены.
    С эмодзи ❌ по ТЗ.
    
    Returns:
        ReplyKeyboardMarkup с кнопкой отмены
    """
    keyboard = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

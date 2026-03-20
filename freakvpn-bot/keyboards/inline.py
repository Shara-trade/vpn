"""
Inline-клавиатуры для пользователя.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict


# ================== СТАРТОВОЕ МЕНЮ ==================

def get_start_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура стартового экрана.
    
    Returns:
        InlineKeyboardMarkup с кнопками старта
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🚀 Получить пробный период",
                callback_data="trial_get"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔑 У меня есть ключ",
                callback_data="have_key"
            )
        ],
        [
            InlineKeyboardButton(
                text="📱 О приложении v2RayTun",
                callback_data="about_app"
            ),
            InlineKeyboardButton(
                text="❓ Как выбрать сервер?",
                callback_data="servers_info"
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== МОЙ КЛЮЧ ==================

def get_key_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура раздела "Мой ключ".
    
    Returns:
        InlineKeyboardMarkup с кнопками управления ключом
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 Скопировать ключ",
                callback_data="copy_key"
            )
        ],
        [
            InlineKeyboardButton(
                text="📱 Инструкция iOS",
                callback_data="guide_ios"
            ),
            InlineKeyboardButton(
                text="🤖 Инструкция Android",
                callback_data="guide_android"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Сменить ключ",
                callback_data="regenerate_key"
            ),
            InlineKeyboardButton(
                text="🌍 Сменить сервер",
                callback_data="change_server"
            ),
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main"
            ),
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОФИЛЬ ==================

def get_profile_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """
    Клавиатура раздела "Профиль".
    
    Args:
        referral_link: Реферальная ссылка пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопками профиля
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой",
                switch_inline_query=referral_link
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 История операций",
                callback_data="balance_history"
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Пополнить баланс",
                url="https://t.me/FreakVPN_Shop"
            ),
            InlineKeyboardButton(
                text="💰 Я оплатил",
                callback_data="check_payment"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎁 Активировать промокод",
                callback_data="enter_promo"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main"
            ),
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой возврата в профиль.
    
    Returns:
        InlineKeyboardMarkup с кнопкой назад
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="◀️ Назад в профиль",
                callback_data="go_to_profile"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ТАРИФЫ ==================

def get_tariffs_keyboard(tariffs: List[Dict], balance: int) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тарифа.
    
    Args:
        tariffs: Список тарифов из БД
        balance: Баланс пользователя в копейках
        
    Returns:
        InlineKeyboardMarkup с кнопками тарифов
    """
    keyboard = []
    
    for tariff in tariffs:
        price_rub = tariff["price"] // 100
        is_affordable = balance >= tariff["price"]
        emoji = "✅" if is_affordable else "❌"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{emoji} {tariff['name']} - {price_rub} ₽",
                callback_data=f"buy_tariff_{tariff['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_main"
        ),
        InlineKeyboardButton(
            text="❌ Закрыть",
            callback_data="close_message"
        ),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_confirm_keyboard(tariff_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения покупки.
    
    Args:
        tariff_id: ID тарифа
        
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"confirm_purchase_{tariff_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_purchase"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_success_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура после успешной покупки.
    
    Returns:
        InlineKeyboardMarkup с навигационными кнопками
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 Скопировать ключ",
                callback_data="copy_key"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔌 Перейти в Мой ключ",
                callback_data="go_to_key"
            ),
            InlineKeyboardButton(
                text="📊 В профиль",
                callback_data="go_to_profile"
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_error_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура при ошибке покупки (недостаточно средств).
    
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="💬 Пополнить баланс",
                url="https://t.me/FreakVPN_Shop"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Проверить баланс",
                callback_data="show_profile"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== СЕРВЕРЫ ==================

def get_servers_keyboard(servers: List[Dict], current_server_id: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сервера.
    
    Args:
        servers: Список серверов из БД
        current_server_id: ID текущего сервера пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопками серверов
    """
    keyboard = []
    
    # Маппинг кодов стран на эмодзи
    country_flags = {
        "NL": "🇳🇱",
        "DE": "🇩🇪",
        "FI": "🇫🇮",
        "US": "🇺🇸",
        "SG": "🇸🇬",
    }
    
    for server in servers:
        flag = country_flags.get(server["country_code"], "🌍")
        is_current = server["id"] == current_server_id
        marker = " ✓" if is_current else ""
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{flag} {server['name']}{marker}",
                callback_data=f"select_server_{server['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_key"
        ),
        InlineKeyboardButton(
            text="❌ Закрыть",
            callback_data="close_message"
        ),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПОДДЕРЖКА ==================

def get_support_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура раздела поддержки.
    
    Returns:
        InlineKeyboardMarkup с кнопками поддержки
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="💬 Написать в поддержку",
                url="https://t.me/FreakVPN_Support"
            )
        ],
        [
            InlineKeyboardButton(
                text="📱 Часто задаваемые вопросы",
                callback_data="show_faq"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_main"
            ),
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== РЕФЕРАЛЫ ==================

def get_referral_keyboard(referrer_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура активации реферального бонуса.
    
    Args:
        referrer_id: ID пригласившего пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопкой активации
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🎁 Активировать бонус",
                callback_data=f"activate_ref_{referrer_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== НАВИГАЦИЯ ==================

def get_back_keyboard(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой назад.
    
    Args:
        callback_data: Callback для кнопки назад
        
    Returns:
        InlineKeyboardMarkup с кнопкой назад
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=callback_data
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_close_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой закрыть (удалить сообщение).
    
    Returns:
        InlineKeyboardMarkup с кнопкой закрыть
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_and_close_keyboard(back_callback: str = "back_to_main") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками назад и закрыть.
    
    Args:
        back_callback: Callback для кнопки назад
        
    Returns:
        InlineKeyboardMarkup с кнопками
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=back_callback
            ),
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data="close_message"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой возврата в главное меню.
    
    Returns:
        InlineKeyboardMarkup с кнопкой назад
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🦎 В главное меню",
                callback_data="back_to_main"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_navigation_keyboard() -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура навигации.
    
    Returns:
        InlineKeyboardMarkup с кнопками навигации
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔌 Мой ключ",
                callback_data="go_to_key"
            ),
            InlineKeyboardButton(
                text="📊 Профиль",
                callback_data="go_to_profile"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_regenerate_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения смены ключа.
    
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Да, сменить ключ",
                callback_data="confirm_regenerate"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_regenerate"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

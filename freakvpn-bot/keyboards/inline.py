"""
Inline-клавиатуры для пользователя.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.models import Server, Tariff


def get_start_keyboard(is_new_user: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура стартового экрана."""
    keyboard = []
    
    if is_new_user:
        keyboard.append([
            InlineKeyboardButton(text="🚀 Получить пробный период", callback_data="trial_get")
        ])
    
    keyboard.extend([
        [InlineKeyboardButton(text="🔑 У меня есть ключ", callback_data="have_key")],
        [InlineKeyboardButton(text="📱 О приложении v2RayTun", callback_data="about_app")],
        [InlineKeyboardButton(text="❓ Как выбрать сервер?", callback_data="servers_info")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_key_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела 'Мой ключ'."""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Скопировать ключ", callback_data="copy_key")
        ],
        [
            InlineKeyboardButton(text="📱 Инструкция iOS", callback_data="guide_ios"),
            InlineKeyboardButton(text="🤖 Инструкция Android", callback_data="guide_android")
        ],
        [
            InlineKeyboardButton(text="🔄 Сменить ключ", callback_data="regenerate_key"),
            InlineKeyboardButton(text="🌍 Сменить сервер", callback_data="change_server")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля."""
    keyboard = [
        [
            InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query="referral")
        ],
        [
            InlineKeyboardButton(text="📊 История операций", callback_data="balance_history")
        ],
        [
            InlineKeyboardButton(text="💬 Пополнить баланс", url="https://t.me/FreakVPN_Shop")
        ],
        [
            InlineKeyboardButton(text="🎁 Активировать промокод", callback_data="enter_promo")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tariffs_keyboard(tariffs: list[Tariff], balance: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа."""
    keyboard = []
    
    for tariff in tariffs:
        price_rub = tariff.price // 100
        can_afford = tariff.price <= balance
        
        text = f"{tariff.name} - {price_rub} ₽"
        if not can_afford:
            text += " ❌"
        
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"buy_tariff_{tariff.months}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_confirm_keyboard(months: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения покупки."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_purchase_{months}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_purchase")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_success_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после успешной покупки."""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Скопировать ключ", callback_data="copy_key")
        ],
        [
            InlineKeyboardButton(text="🔌 Перейти в Мой ключ", callback_data="go_to_key"),
            InlineKeyboardButton(text="📊 В профиль", callback_data="go_to_profile")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_servers_keyboard(servers: list[Server], current_server_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора сервера."""
    keyboard = []
    
    for server in servers:
        marker = "✓ " if server.id == current_server_id else ""
        text = f"{marker}{server.flag} {server.name}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"select_server_{server.id}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_keyboard(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад'."""
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_support_keyboard(support_contact: str, payment_contact: str) -> InlineKeyboardMarkup:
    """Клавиатура поддержки."""
    keyboard = [
        [
            InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{support_contact.lstrip('@')}")
        ],
        [
            InlineKeyboardButton(text="📱 Часто задаваемые вопросы", callback_data="show_faq")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_referral_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Клавиатура реферальной системы."""
    keyboard = [
        [
            InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query="referral")
        ],
        [
            InlineKeyboardButton(text="📊 История операций", callback_data="balance_history")
        ],
        [
            InlineKeyboardButton(text="💬 Пополнить баланс", url="https://t.me/FreakVPN_Shop")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_referral_activate_keyboard(referral_code: str) -> InlineKeyboardMarkup:
    """Клавиатура активации реферального бонуса."""
    keyboard = [
        [
            InlineKeyboardButton(text="🎁 Активировать бонус", callback_data=f"activate_ref_{referral_code}")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_trial_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после активации пробного периода."""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Скопировать ключ", callback_data="copy_key")
        ],
        [
            InlineKeyboardButton(text="📱 Инструкция", callback_data="guide_main")
        ],
        [
            InlineKeyboardButton(text="🦎 В главное меню", callback_data="back_to_main")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_balance_error_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при недостаточном балансе."""
    keyboard = [
        [
            InlineKeyboardButton(text="💬 Пополнить баланс", url="https://t.me/FreakVPN_Shop")
        ],
        [
            InlineKeyboardButton(text="📊 Проверить баланс", callback_data="show_profile")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

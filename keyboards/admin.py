"""
Inline-клавиатуры для администратора.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict


# ================== ПОЛЬЗОВАТЕЛИ ==================

def get_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с пользователем.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="💰 Пополнить баланс",
                callback_data=f"admin_add_balance_{user_id}"
            ),
            InlineKeyboardButton(
                text="➖ Списать баланс",
                callback_data=f"admin_withdraw_balance_{user_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="➕ Продлить подписку",
                callback_data=f"admin_extend_{user_id}"
            ),
            InlineKeyboardButton(
                text="🔄 Сменить ключ",
                callback_data=f"admin_reset_key_{user_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="➖ Заблокировать",
                callback_data=f"admin_block_{user_id}"
            ),
            InlineKeyboardButton(
                text="📊 История операций",
                callback_data=f"admin_history_{user_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_balance_confirm_keyboard(amount: int, user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения начисления баланса.
    
    Args:
        amount: Сумма в копейках
        user_id: Telegram ID пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить начисление",
                callback_data=f"admin_confirm_add_{amount}_{user_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="admin_cancel"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== СЕРВЕРЫ ==================

def get_admin_servers_keyboard(servers: List[Dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура управления серверами.
    
    Args:
        servers: Список серверов
        
    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Добавить сервер",
                callback_data="admin_add_server"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data="admin_edit_servers"
            ),
            InlineKeyboardButton(
                text="🔄 Проверить статус",
                callback_data="admin_check_servers"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_server_actions_keyboard(server_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с сервером.
    
    Args:
        server_id: ID сервера
        is_active: Активен ли сервер
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    toggle_text = "❌ Отключить" if is_active else "✅ Включить"
    toggle_action = "deactivate" if is_active else "activate"
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=f"admin_server_{toggle_action}_{server_id}"
            ),
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"admin_server_delete_{server_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin_servers"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== РАССЫЛКА ==================

def get_admin_mailing_keyboard(total_users: int) -> InlineKeyboardMarkup:
    """
    Клавиатура рассылки.
    
    Args:
        total_users: Общее количество пользователей
        
    Returns:
        InlineKeyboardMarkup с кнопками рассылки
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"✅ Отправить всем ({total_users})",
                callback_data="admin_send_all"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔁 Отправить тест себе",
                callback_data="admin_send_test"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="admin_cancel"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== НАСТРОЙКИ ==================

def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура настроек бота.
    
    Returns:
        InlineKeyboardMarkup с кнопками настроек
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Изменить тарифы",
                callback_data="admin_edit_prices"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить пробный период",
                callback_data="admin_edit_trial"
            ),
            InlineKeyboardButton(
                text="✏️ Изменить контакты",
                callback_data="admin_edit_contacts"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_tariffs_keyboard(tariffs: List[Dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тарифа для редактирования.
    
    Args:
        tariffs: Список тарифов
        
    Returns:
        InlineKeyboardMarkup с кнопками тарифов
    """
    keyboard = []
    
    for tariff in tariffs:
        price_rub = tariff["price"] // 100
        keyboard.append([
            InlineKeyboardButton(
                text=f"{tariff['name']} - {price_rub} ₽",
                callback_data=f"admin_edit_tariff_{tariff['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_settings"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ОБЩИЕ ==================

def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены.
    
    Returns:
        InlineKeyboardMarkup с кнопкой отмены
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="admin_cancel"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_back_keyboard(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
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


# ================== СПИСАНИЕ БАЛАНСА ==================

def get_admin_withdraw_confirm_keyboard(amount: int, user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения списания баланса.
    
    Args:
        amount: Сумма в копейках
        user_id: Telegram ID пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить списание",
                callback_data=f"admin_confirm_withdraw_{amount}_{user_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="admin_cancel"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ЛОГИ ==================

def get_admin_logs_keyboard(categories: List[str]) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора категории логов.
    
    Args:
        categories: Список категорий
        
    Returns:
        InlineKeyboardMarkup с кнопками категорий
    """
    cat_names = {
        "user": "👤 Пользователи",
        "payment": "💰 Платежи",
        "subscription": "📅 Подписки",
        "key": "🔑 Ключи",
        "server": "🌍 Серверы",
        "admin": "👑 Админ",
        "referral": "🎁 Рефералы",
        "promocode": "🏷️ Промокоды",
        "error": "⚠️ Ошибки",
        "system": "⚙️ Система",
    }
    
    keyboard = []
    
    for cat in categories:
        text = cat_names.get(cat, cat)
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"admin_logs_{cat}")])
    
    keyboard.append([InlineKeyboardButton(text="🗑 Очистить старые (30+ дней)", callback_data="admin_logs_clean")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОМОКОДЫ ==================

def get_admin_promocodes_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления промокодами.
    
    Returns:
        InlineKeyboardMarkup с кнопками
    """
    keyboard = [
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_promo_type_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора типа промокода.
    
    Returns:
        InlineKeyboardMarkup с кнопками типов
    """
    keyboard = [
        [InlineKeyboardButton(text="🏷️ Скидка %", callback_data="promo_type_discount_percent")],
        [InlineKeyboardButton(text="🏷️ Скидка ₽", callback_data="promo_type_discount_fixed")],
        [InlineKeyboardButton(text="🎁 Бесплатные дни", callback_data="promo_type_free_days")],
        [InlineKeyboardButton(text="💰 На баланс", callback_data="promo_type_balance")],
        [InlineKeyboardButton(text="📅 Продление подписки", callback_data="promo_type_subscription_extension")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_search_again_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для повторного поиска.
    
    Returns:
        InlineKeyboardMarkup с кнопками
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔍 Найти другого",
                callback_data="admin_search_again"
            ),
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin_main"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

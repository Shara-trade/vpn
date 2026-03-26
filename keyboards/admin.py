"""
Inline-клавиатуры для администратора (StarinaVPN).
Все кнопки 'Назад' и 'Закрыть' без эмодзи по ТЗ.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict


def _add_admin_navigation(keyboard: list, back_callback: str = "admin_main") -> list:
    """Добавление кнопок Назад и Закрыть (без эмодзи)."""
    keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data=back_callback),
        InlineKeyboardButton(text="Закрыть", callback_data="close_message"),
    ])
    return keyboard
    

# ================== ПОЛЬЗОВАТЕЛИ ==================

def get_user_actions_keyboard(user_id: int, is_blocked: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура действий с пользователем."""
    block_text = "✅ Разблокировать" if is_blocked else "🚫 Заблокировать"
    
    keyboard = [
        [
            InlineKeyboardButton(text="💰 Пополнить баланс", callback_data=f"admin_add_balance_{user_id}"),
            InlineKeyboardButton(text="➖ Списать баланс", callback_data=f"admin_withdraw_balance_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="➕ Продлить подписку", callback_data=f"admin_extend_{user_id}"),
            InlineKeyboardButton(text="🔄 Сменить ключ", callback_data=f"admin_reset_key_{user_id}"),
        ],
        [
            InlineKeyboardButton(text=block_text, callback_data=f"admin_block_{user_id}"),
            InlineKeyboardButton(text="📊 История операций", callback_data=f"admin_history_{user_id}"),
        ],
    ]
    _add_admin_navigation(keyboard, "admin_users")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_users_list_keyboard(users: List[Dict], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """
    Клавиатура списка пользователей с пагинацией.
    
    Args:
        users: Список пользователей
        page: Текущая страница
        per_page: Пользователей на странице
    """
    keyboard = []
    
    for user in users[page*per_page:(page+1)*per_page]:
        name = user.get("username") or user.get("full_name") or f"ID:{user['user_id']}"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{name}", 
                callback_data=f"admin_user_{user['user_id']}"
            )
        ])
    
    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="«", callback_data=f"admin_users_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}", callback_data="admin_nop"))
    if len(users) > (page+1)*per_page:
        nav_row.append(InlineKeyboardButton(text="»", callback_data=f"admin_users_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    _add_admin_navigation(keyboard, "admin_main")
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
    """Клавиатура управления серверами."""
    keyboard = [[InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server")]]
    
    for server in servers:
        status = "🟢" if server.get("is_active") else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {server['name']} ({server.get('load', 0)} users)",
                callback_data=f"admin_server_{server['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Проверить статус всех", callback_data="admin_check_servers")])
    _add_admin_navigation(keyboard, "admin_other")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_server_actions_keyboard(server_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура действий с сервером."""
    toggle_text = "❌ Отключить" if is_active else "✅ Включить"
    toggle_action = "deactivate" if is_active else "activate"
    
    keyboard = [
        [
            InlineKeyboardButton(text=toggle_text, callback_data=f"admin_server_{toggle_action}_{server_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_server_delete_{server_id}"),
        ],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_server_edit_{server_id}")],
        [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"admin_server_check_{server_id}")],
    ]
    _add_admin_navigation(keyboard, "admin_servers")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОЧЕЕ (новый раздел по ТЗ) ==================

def get_admin_other_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела 'Прочее'."""
    keyboard = [
        [InlineKeyboardButton(text="💰 Тарифы", callback_data="admin_tariffs")],
        [InlineKeyboardButton(text="📝 Реквизиты", callback_data="admin_payment_details")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="admin_contacts")],
        [InlineKeyboardButton(text="🌍 Серверы", callback_data="admin_servers")],
        [InlineKeyboardButton(text="🎁 Пробный период", callback_data="admin_trial_settings")],
        [InlineKeyboardButton(text="👥 Реферальный бонус", callback_data="admin_referral_settings")],
        [InlineKeyboardButton(text="💸 Минимальная сумма", callback_data="admin_min_topup")],
    ]
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== РАССЫЛКА ==================

def get_admin_mailing_keyboard(total_users: int) -> InlineKeyboardMarkup:
    """Клавиатура рассылки."""
    keyboard = [
        [InlineKeyboardButton(text=f"✅ Отправить всем ({total_users})", callback_data="admin_send_all")],
        [
            InlineKeyboardButton(text="🔁 Отправить тест себе", callback_data="admin_send_test"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== НАСТРОЙКИ ==================

def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек бота."""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить тарифы", callback_data="admin_edit_prices")],
        [InlineKeyboardButton(text="✏️ Изменить пробный период", callback_data="admin_edit_trial")],
        [InlineKeyboardButton(text="✏️ Изменить контакты", callback_data="admin_edit_contacts")],
        [InlineKeyboardButton(text="✏️ Реферальная система", callback_data="admin_edit_referral")],
    ]
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_tariffs_keyboard(tariffs: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа для редактирования."""
    keyboard = []
    
    for tariff in tariffs:
        price_rub = tariff["price"] // 100
        keyboard.append([
            InlineKeyboardButton(
                text=f"{tariff['name']} — {price_rub} ₽",
                callback_data=f"admin_edit_tariff_{tariff['id']}"
            )
        ])
    
    _add_admin_navigation(keyboard, "admin_other")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ОБЩИЕ ==================

def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    keyboard = [[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_back_keyboard(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад (без эмодзи)."""
    keyboard = [[InlineKeyboardButton(text="Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_back_and_close_keyboard(back_callback: str = "admin_main") -> InlineKeyboardMarkup:
    """Клавиатура с кнопками назад и закрыть (без эмодзи)."""
    keyboard = [
        [
            InlineKeyboardButton(text="Назад", callback_data=back_callback),
            InlineKeyboardButton(text="Закрыть", callback_data="close_message"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== СПИСАНИЕ БАЛАНСА ==================

def get_admin_withdraw_confirm_keyboard(amount: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения списания баланса."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить списание", callback_data=f"admin_confirm_withdraw_{amount}_{user_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_balance_confirm_keyboard(amount: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения начисления баланса."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить начисление", callback_data=f"admin_confirm_add_{amount}_{user_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ЛОГИ ==================

def get_admin_logs_keyboard(categories: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории логов."""
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
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_logs_category_keyboard(category: str) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра логов категории."""
    keyboard = [
        [InlineKeyboardButton(text="🗑 Очистить старые", callback_data=f"admin_logs_clean_{category}")],
    ]
    _add_admin_navigation(keyboard, "admin_logs")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОМОКОДЫ ==================

def get_admin_promocodes_keyboard(promocodes: List[Dict] = None) -> InlineKeyboardMarkup:
    """Клавиатура управления промокодами."""
    keyboard = [[InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")]]
    
    if promocodes:
        for promo in promocodes:
            status = "🟢" if promo.get("is_active") else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {promo['code']} ({promo['used_count']}/{promo.get('max_uses', '∞')})",
                    callback_data=f"admin_promo_{promo['id']}"
                )
            ])
    
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_promo_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа промокода."""
    keyboard = [
        [InlineKeyboardButton(text="🏷️ Скидка %", callback_data="promo_type_discount_percent")],
        [InlineKeyboardButton(text="🏷️ Скидка ₽", callback_data="promo_type_discount_fixed")],
        [InlineKeyboardButton(text="🎁 Бесплатные дни", callback_data="promo_type_free_days")],
        [InlineKeyboardButton(text="💰 На баланс", callback_data="promo_type_balance")],
        [InlineKeyboardButton(text="📅 Продление подписки", callback_data="promo_type_subscription_extension")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_promo_actions_keyboard(promo_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура действий с промокодом."""
    toggle_text = "❌ Деактивировать" if is_active else "✅ Активировать"
    toggle_callback = f"admin_promo_deactivate_{promo_id}" if is_active else f"admin_promo_activate_{promo_id}"
    
    keyboard = [
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_callback)],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_promo_delete_{promo_id}")],
    ]
    _add_admin_navigation(keyboard, "admin_promocodes")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_search_again_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для повторного поиска."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔍 Найти другого", callback_data="admin_search_again"),
            InlineKeyboardButton(text="Назад", callback_data="admin_main"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

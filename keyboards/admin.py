"""
Inline-клавиатуры для администратора (StarinaVPN).
Все кнопки 'Назад' и 'Закрыть' без эмодзи по ТЗ.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict


# ================== ГЛАВНАЯ АДМИН КЛАВИАТУРА (Reply) ==================

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура админ-панели (Reply-кнопки)."""
    keyboard = [
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🌍 Серверы"), KeyboardButton(text="⚙️ Прочее")],
        [KeyboardButton(text="📋 Логи"), KeyboardButton(text="🎫 Промокоды")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="📨 Рассылка")],
        [KeyboardButton(text="❌ Закрыть")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


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


def get_admin_topup_keyboard(user_id: int, amount: int) -> InlineKeyboardMarkup:
    """Клавиатура для администратора при заявке на пополнение."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Пополнить", callback_data=f"admin_add_balance_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_payment_{user_id}_{amount}"),
        ],
        [InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
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


# ================== ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ==================

def get_delete_confirm_keyboard(delete_callback: str, back_callback: str = "admin_main") -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления.
    
    Args:
        delete_callback: callback_data для подтверждения удаления
        back_callback: callback_data для возврата
    """
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=delete_callback),
            InlineKeyboardButton(text="❌ Отмена", callback_data=back_callback),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_server_delete_confirm_keyboard(server_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления сервера."""
    return get_delete_confirm_keyboard(
        delete_callback=f"admin_confirm_delete_server_{server_id}",
        back_callback=f"admin_server_{server_id}"
    )


def get_promo_delete_confirm_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления промокода."""
    return get_delete_confirm_keyboard(
        delete_callback=f"admin_confirm_delete_promo_{promo_id}",
        back_callback=f"admin_promo_{promo_id}"
    )


def get_key_delete_confirm_keyboard(key_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления ключа пользователя."""
    return get_delete_confirm_keyboard(
        delete_callback=f"admin_confirm_delete_key_{key_id}_{user_id}",
        back_callback=f"admin_user_{user_id}"
    )


def get_user_block_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения блокировки пользователя."""
    return get_delete_confirm_keyboard(
        delete_callback=f"admin_confirm_block_{user_id}",
        back_callback=f"admin_user_{user_id}"
    )


# ================== НОВЫЕ КЛАВИАТУРЫ ПО ТЗ ==================

def get_admin_users_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела Пользователи (1.2)."""
    keyboard = [
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_user_search")],
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list")],
    ]
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_user_search_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для поиска пользователя (1.2.1)."""
    keyboard = [
        [InlineKeyboardButton(text="Назад", callback_data="admin_users")],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_users_list_keyboard(users: List[Dict], page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    """
    Клавиатура списка пользователей с пагинацией по 8 (1.2.2).
    Формат: 👤 @username — 500₽ — ✅
    """
    keyboard = []
    total_pages = (len(users) + per_page - 1) // per_page
    
    for user in users[page*per_page:(page+1)*per_page]:
        name = f"@{user.get('username', '')}" if user.get('username') else f"ID:{user['user_id']}"
        balance = user.get('balance', 0) // 100
        status_icon = "ON" if user.get('status') == 'active' else "OFF"
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {name} - {balance}RUB - {status_icon}",
                callback_data=f"admin_user_{user['user_id']}"
            )
        ])
    
    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="«", callback_data=f"admin_users_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="admin_nop"))
    if len(users) > (page+1)*per_page:
        nav_row.append(InlineKeyboardButton(text="»", callback_data=f"admin_users_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="admin_users"),
        InlineKeyboardButton(text="Закрыть", callback_data="close_message"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_user_card_keyboard(user_id: int, is_blocked: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура карточки пользователя (1.2.3).
    """
    block_text = "✅ Разблокировать" if is_blocked else "🚫 Заблокировать"
    
    keyboard = [
        [
            InlineKeyboardButton(text="💰 Пополнить", callback_data=f"admin_add_balance_{user_id}"),
            InlineKeyboardButton(text="➖ Списать", callback_data=f"admin_withdraw_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="➕ Продлить", callback_data=f"admin_extend_{user_id}"),
            InlineKeyboardButton(text="🔄 Сменить ключ", callback_data=f"admin_reset_key_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить ключ", callback_data=f"admin_delete_key_{user_id}"),
        ],
        [
            InlineKeyboardButton(text=block_text, callback_data=f"admin_block_{user_id}"),
            InlineKeyboardButton(text="📋 История", callback_data=f"admin_history_{user_id}"),
        ],
    ]
    _add_admin_navigation(keyboard, "admin_users_list")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура статистики (1.3)."""
    keyboard = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats_refresh")],
    ]
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_servers_list_keyboard(servers: List[Dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура управления серверами (1.4).
    Формат: ✅ 🇳🇱 Амстердам — 45 польз. — нагрузка 23%
    """
    keyboard = []
    
    for server in servers:
        status = "✅" if server.get("is_active") else "❌"
        flag = get_country_flag(server.get("country_code", ""))
        users_count = server.get("users_count", 0)
        load = server.get("load", 0)
        capacity = server.get("capacity", 200) or 200
        load_percent = int(load / capacity * 100) if capacity > 0 else 0
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {flag} {server['name']} — {users_count} польз. — нагрузка {load_percent}%",
                callback_data=f"admin_server_card_{server['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server"),
        InlineKeyboardButton(text="🔄 Проверить все", callback_data="admin_check_all_servers"),
    ])
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_server_card_keyboard(server_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура карточки сервера (1.4.2)."""
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отключить" if is_active else "✅ Включить", 
                                callback_data=f"admin_server_toggle_{server_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_server_delete_{server_id}"),
        ],
        [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"admin_server_check_{server_id}")],
    ]
    _add_admin_navigation(keyboard, "admin_servers")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_other_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела Прочее (1.5)."""
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


def get_admin_logs_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории логов (1.6)."""
    keyboard = [
        [InlineKeyboardButton(text="👤 Пользователи", callback_data="admin_logs_user")],
        [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_logs_payment")],
        [InlineKeyboardButton(text="📅 Подписки", callback_data="admin_logs_subscription")],
        [InlineKeyboardButton(text="🔑 Ключи", callback_data="admin_logs_key")],
        [InlineKeyboardButton(text="🌍 Серверы", callback_data="admin_logs_server")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin_logs_admin")],
        [InlineKeyboardButton(text="🎁 Рефералы", callback_data="admin_logs_referral")],
        [InlineKeyboardButton(text="🏷️ Промокоды", callback_data="admin_logs_promocode")],
        [InlineKeyboardButton(text="⚠️ Ошибки", callback_data="admin_logs_error")],
        [InlineKeyboardButton(text="⚙️ Система", callback_data="admin_logs_system")],
        [InlineKeyboardButton(text="🗑 Очистить старые (30+ дней)", callback_data="admin_logs_clean_all")],
    ]
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_logs_view_keyboard(category: str, page: int = 0, has_next: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура просмотра логов (1.6)."""
    keyboard = []
    
    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_logs_{category}_page_{page-1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_logs_{category}_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([
        InlineKeyboardButton(text="🗑 Очистить категорию", callback_data=f"admin_logs_clean_{category}"),
    ])
    _add_admin_navigation(keyboard, "admin_logs")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_promocodes_list_keyboard(promocodes: List[Dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура управления промокодами (1.7).
    Формат: ✅ WELCOME15 — скидка 15% — 45/100 — до 01.05.2025
    """
    keyboard = []
    
    for promo in promocodes:
        status = "✅" if promo.get("is_active") else "❌"
        code = promo.get("code", "")
        promo_type = promo.get("type", "")
        
        # Форматируем тип
        if promo_type == "discount_percent":
            type_text = f"скидка {promo.get('value', 0)}%"
        elif promo_type == "discount_fixed":
            type_text = f"{promo.get('value', 0) // 100}₽"
        elif promo_type == "free_days":
            type_text = f"{promo.get('value', 0)} дней бесплатно"
        elif promo_type == "balance":
            type_text = f"{promo.get('value', 0) // 100}₽ на баланс"
        else:
            type_text = promo_type
        
        used = promo.get("used_count", 0)
        max_uses = promo.get("max_uses", 0)
        limit_text = f"{used}/{max_uses}" if max_uses > 0 else f"{used}/∞"
        
        expires = promo.get("expires_at")
        if expires:
            from datetime import datetime
            try:
                if isinstance(expires, str):
                    expires_dt = datetime.strptime(expires.replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    expires_dt = expires
                expires_text = expires_dt.strftime("%d.%m.%Y")
            except:
                expires_text = "бессрочно"
        else:
            expires_text = "бессрочно"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {code} — {type_text} — {limit_text} — до {expires_text}",
                callback_data=f"admin_promo_card_{promo['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")])
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_promo_card_keyboard(promo_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура карточки промокода (1.7.1)."""
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Деактивировать" if is_active else "✅ Активировать", 
                                callback_data=f"admin_promo_toggle_{promo_id}"),
            InlineKeyboardButton(text="🗑 Удалить навсегда", callback_data=f"admin_promo_delete_{promo_id}"),
        ],
    ]
    _add_admin_navigation(keyboard, "admin_promocodes")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_promo_create_keyboard(step: int) -> InlineKeyboardMarkup:
    """Клавиатура создания промокода (1.7.2)."""
    keyboard = [
        [InlineKeyboardButton(text="Назад", callback_data="admin_promocodes")],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_settings_menu_keyboard(tariffs: List[Dict], trial_days: int = 3, min_topup: int = 50) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек (1.8).
    """
    keyboard = []
    
    # Тарифы
    tariff_text = "💰 Тарифы:\n"
    for tariff in tariffs:
        price = tariff.get("price", 0) // 100
        days = tariff.get("days", 0)
        if days == 7:
            tariff_text += f"• 7 дней: {price} ₽\n"
            keyboard.append([InlineKeyboardButton(text="✏️ Изменить 7 дней", callback_data="admin_edit_tariff_7")])
        elif days == 30:
            tariff_text += f"• 1 месяц: {price} ₽\n"
            keyboard.append([InlineKeyboardButton(text="✏️ Изменить 1 месяц", callback_data="admin_edit_tariff_30")])
        elif days == 90:
            tariff_text += f"• 3 месяца: {price} ₽\n"
            keyboard.append([InlineKeyboardButton(text="✏️ Изменить 3 месяца", callback_data="admin_edit_tariff_90")])
        elif days == 180:
            tariff_text += f"• 6 месяцев: {price} ₽\n"
            keyboard.append([InlineKeyboardButton(text="✏️ Изменить 6 месяцев", callback_data="admin_edit_tariff_180")])
        elif days == 360:
            tariff_text += f"• 12 месяцев: {price} ₽\n"
            keyboard.append([InlineKeyboardButton(text="✏️ Изменить 12 месяцев", callback_data="admin_edit_tariff_360")])
    
    # Пробный период
    keyboard.append([InlineKeyboardButton(text=f"🎁 Пробный период: {trial_days} дней", callback_data="admin_nop")])
    keyboard.append([InlineKeyboardButton(text="✏️ Изменить пробный период", callback_data="admin_edit_trial")])
    
    # Реквизиты, контакты, рефералы
    keyboard.append([
        InlineKeyboardButton(text="💳 Реквизиты оплаты", callback_data="admin_payment_details"),
        InlineKeyboardButton(text="📞 Контакты", callback_data="admin_contacts"),
    ])
    keyboard.append([
        InlineKeyboardButton(text="👥 Реферальная система", callback_data="admin_referral_settings"),
    ])
    
    # Минимальная сумма
    keyboard.append([
        InlineKeyboardButton(text=f"💸 Минимальное пополнение: {min_topup} ₽", callback_data="admin_nop"),
        InlineKeyboardButton(text="✏️ Изменить", callback_data="admin_edit_min_topup"),
    ])
    
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_mailing_audience_keyboard(audience_stats: Dict) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора аудитории для рассылки (1.9).
    """
    keyboard = [
        [InlineKeyboardButton(text=f"👥 Всем пользователям — {audience_stats.get('all', 0)} чел.", 
                             callback_data="admin_mailing_all")],
        [InlineKeyboardButton(text=f"🔑 Активным ключам — {audience_stats.get('active_keys', 0)} чел.", 
                             callback_data="admin_mailing_active_keys")],
        [InlineKeyboardButton(text="🌍 По серверу", callback_data="admin_mailing_by_server")],
        [InlineKeyboardButton(text=f"💰 С балансом >0 — {audience_stats.get('has_balance', 0)} чел.", 
                             callback_data="admin_mailing_has_balance")],
        [InlineKeyboardButton(text=f"🎁 Не использовавшим промокоды — {audience_stats.get('no_promo', 0)} чел.", 
                             callback_data="admin_mailing_no_promo")],
        [InlineKeyboardButton(text=f"📅 С истекающей подпиской (3 дня) — {audience_stats.get('expiring', 0)} чел.", 
                             callback_data="admin_mailing_expiring")],
        [InlineKeyboardButton(text=f"🔄 С автопродлением — {audience_stats.get('autorenew', 0)} чел.", 
                             callback_data="admin_mailing_autorenew")],
    ]
    _add_admin_navigation(keyboard, "admin_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_mailing_preview_keyboard(audience_type: str, recipients_count: int) -> InlineKeyboardMarkup:
    """Клавиатура предпросмотра рассылки (1.9)."""
    keyboard = [
        [InlineKeyboardButton(text=f"✅ Отправить всем ({recipients_count})", 
                             callback_data=f"admin_mailing_send_{audience_type}")],
        [InlineKeyboardButton(text="🔁 Отправить тест себе", callback_data="admin_mailing_test")],
        [InlineKeyboardButton(text="⬅️ Другая аудитория", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_mailing_progress_keyboard(sent: int, total: int) -> InlineKeyboardMarkup:
    """Клавиатура прогресса рассылки (1.9)."""
    percent = int(sent / total * 100) if total > 0 else 0
    keyboard = [
        [InlineKeyboardButton(text=f"📨 Отправлено: {sent} из {total} ({percent}%)", callback_data="admin_nop")],
        [InlineKeyboardButton(text="⏹ Остановить", callback_data="admin_mailing_stop")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_country_flag(country_code: str) -> str:
    """Получение флага по коду страны."""
    flags = {
        "NL": "🇳🇱",
        "DE": "🇩🇪",
        "FI": "🇫🇮",
        "US": "🇺🇸",
        "SG": "🇸🇬",
        "RU": "🇷🇺",
        "UA": "🇺🇦",
        "KZ": "🇰🇿",
        "BY": "🇧🇾",
    }
    return flags.get(country_code, "🌍")

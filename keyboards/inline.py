"""
Inline-клавиатуры для пользователя (StarinaVPN).
Все кнопки "Назад" и "Закрыть" без эмодзи по ТЗ.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Optional


# ================== УТИЛИТЫ ==================

def _add_navigation(keyboard: list, back_callback: str = "back_to_main") -> list:
    """Добавление кнопок Назад и Закрыть (без эмодзи)."""
    keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data=back_callback),
        InlineKeyboardButton(text="Закрыть", callback_data="close_message"),
    ])
    return keyboard
    

# ================== СТАРТОВОЕ МЕНЮ ==================

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура стартового экрана."""
    keyboard = [
        [InlineKeyboardButton(text="🚀 Получить пробный период", callback_data="trial_get")],
        [InlineKeyboardButton(text="🔑 У меня есть ключ", callback_data="have_key")],
        [InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== МОИ КЛЮЧИ ==================
# Поддержка до 5 ключей с переключением

def get_keys_keyboard(
    key_id: int,
    has_prev: bool,
    has_next: bool,
    auto_renew: bool,
    server_id: int
) -> InlineKeyboardMarkup:
    """
    Клавиатура раздела 'Мои ключи'.
    
    Args:
        key_id: ID текущего ключа
        has_prev: Есть предыдущий ключ
        has_next: Есть следующий ключ
        auto_renew: Включено автопродление
        server_id: ID сервера
    """
    keyboard = []
    
    # Стрелки переключения
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="«", callback_data=f"key_prev_{key_id}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="»", callback_data=f"key_next_{key_id}"))
    if nav_row:
        keyboard.append(nav_row)
    
    # Основные действия
    keyboard.append([
        InlineKeyboardButton(text="📋 Скопировать ключ", callback_data=f"copy_key_{key_id}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⏳ Продлить", callback_data=f"extend_key_{key_id}"),
        InlineKeyboardButton(text="🔄 Сменить ключ", callback_data=f"change_key_{key_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton(text="🗑 Удалить ключ", callback_data=f"delete_key_{key_id}"),
    ])
    
    # Автопродление
    renew_status = "✅ Вкл" if auto_renew else "❌ Выкл"
    keyboard.append([
        InlineKeyboardButton(text=f"🔄 Автопродление: {renew_status}", callback_data=f"toggle_autorenew_{key_id}"),
    ])
    
    # Инструкция
    keyboard.append([
        InlineKeyboardButton(text="📱 Инструкция", callback_data=f"guide_key_{key_id}"),
    ])
    
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_key_change_confirm_keyboard(key_id: int) -> InlineKeyboardMarkup:
    """Подтверждение смены ключа."""
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, сменить", callback_data=f"confirm_change_key_{key_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"key_details_{key_id}"), 
         InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_key_delete_confirm_keyboard(key_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления ключа."""
    keyboard = [
        [InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"confirm_delete_key_{key_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"key_details_{key_id}"), 
         InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_keys_empty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура когда нет ключей."""
    keyboard = [
        [InlineKeyboardButton(text="💰 Купить ключ", callback_data="go_to_buy")],
        _add_navigation([], "back_to_main")[0]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОФИЛЬ ==================

def get_profile_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """
    Клавиатура раздела 'Профиль'.
    
    Args:
        referral_link: Реферальная ссылка пользователя
    """
    keyboard = [
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=referral_link)],
        [InlineKeyboardButton(text="📊 История операций", callback_data="balance_history")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="start_topup")],
    ]
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_topup_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню пополнения баланса."""
    keyboard = [
        [InlineKeyboardButton(text="💳 Пополнить", callback_data="start_topup_input")],
        [InlineKeyboardButton(text="💬 Пополнить напрямую", url="https://t.me/StarinaVPN_Shop")],
    ]
    _add_navigation(keyboard, "back_to_profile")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_topup_confirm_keyboard(amount: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения оплаты."""
    keyboard = [
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"topup_paid_{amount}")],
    ]
    _add_navigation(keyboard, "back_to_profile")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в профиль."""
    keyboard = [[InlineKeyboardButton(text="Назад", callback_data="go_to_profile")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== КУПИТЬ / ТАРИФЫ ==================

def get_buy_keyboard(tariffs: List[Dict], has_trial: bool = True, extend_key_id: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура раздела 'Купить'.
    
    Args:
        tariffs: Список тарифов из БД
        has_trial: Использован ли пробный период (True = уже использован)
        extend_key_id: ID ключа для продления (если продление)
    """
    keyboard = []
    
    # Пробный ключ всегда первый (только для новой покупки)
    if not extend_key_id:
        if not has_trial:
            keyboard.append([InlineKeyboardButton(text="🎁 Пробный ключ", callback_data="buy_trial")])
        else:
            keyboard.append([InlineKeyboardButton(text="❌ Пробный ключ (уже использован)", callback_data="trial_used")])
    
    # Платные тарифы
    for tariff in tariffs:
        if tariff["price"] == 0:
            continue  # Пробный уже показали
        price_rub = tariff["price"] // 100
        
        # Формируем callback_data в зависимости от режима
        if extend_key_id:
            callback = f"extend_tariff_{tariff['id']}_{extend_key_id}"
        else:
            callback = f"buy_tariff_{tariff['id']}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{tariff['name']} — {price_rub} ₽",
                callback_data=callback
            )
        ])
    
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tariffs_keyboard(tariffs: List[Dict], balance: int) -> InlineKeyboardMarkup:
    """Устаревшая функция - используйте get_buy_keyboard."""
    return get_buy_keyboard(tariffs, balance, False)


def get_purchase_confirm_keyboard(tariff_id: int, extend_key_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения покупки/продления."""
    if extend_key_id:
        callback = f"confirm_purchase_{tariff_id}_{extend_key_id}"
    else:
        callback = f"confirm_purchase_{tariff_id}"
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=callback)],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_buy"), 
         InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_success_keyboard(key_id: int) -> InlineKeyboardMarkup:
    """Клавиатура после успешной покупки."""
    keyboard = [
        [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="go_to_keys")],
    ]
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_purchase_error_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при ошибке покупки (недостаточно средств)."""
    keyboard = [
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="start_topup")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_buy"), 
         InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПОДДЕРЖКА ==================

def get_support_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела 'Поддержка'."""
    keyboard = [
        [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/StarinaVPN_Support_bot")],
        [InlineKeyboardButton(text="📱 Часто задаваемые вопросы", callback_data="show_faq")],
    ]
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ОТЗЫВЫ ==================

def get_reviews_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела 'Отзывы'."""
    keyboard = [
        [InlineKeyboardButton(text="⭐️ Оставить отзыв", url="https://t.me/StarinaVPN_Support_bot")],
        [InlineKeyboardButton(text="👀 Посмотреть отзывы", url="https://t.me/StarinaVPN_Reviews")],
    ]
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОМОКОД ==================

def get_promocode_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода промокода."""
    keyboard = [
        [InlineKeyboardButton(text="Ввести промокод", callback_data="enter_promocode")],
    ]
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== СТАТУС СЕРВЕРОВ ==================

def get_servers_status_keyboard(servers: List[Dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура статуса серверов.
    
    Args:
        servers: Список серверов из БД
    """
    keyboard = []
    
    country_flags = {
        "NL": "🇳🇱", "DE": "🇩🇪", "FI": "🇫🇮", 
        "US": "🇺🇸", "SG": "🇸🇬",
    }
    
    for server in servers:
        flag = country_flags.get(server["country_code"], "🌍")
        ping = server.get("ping", 0)
        load = server.get("load", 0)
        status = "🟢" if server.get("is_active") else "🔴"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {flag} {server['name']} — {ping}ms ({load}%)",
                callback_data=f"server_info_{server['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_servers_status")])
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_servers_keyboard(servers: List[Dict], current_server_id: int = None) -> InlineKeyboardMarkup:
    """Устаревшая функция выбора сервера."""
    keyboard = []
    
    country_flags = {"NL": "🇳🇱", "DE": "🇩🇪", "FI": "🇫🇮", "US": "🇺🇸", "SG": "🇸🇬"}
    
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
    
    _add_navigation(keyboard, "back_to_key")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== РЕФЕРАЛЬНАЯ СИСТЕМА ==================

def get_referral_keyboard(referrer_id: int) -> InlineKeyboardMarkup:
    """Клавиатура активации реферального бонуса."""
    keyboard = [
        [InlineKeyboardButton(text="🎁 Активировать бонус", callback_data=f"activate_ref_{referrer_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== ПРОВЕРКА ПОДПИСКИ ==================

def get_subscription_check_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Клавиатура проверки подписки на канал.
    
    Args:
        action: Действие, для которого требуется подписка
    """
    keyboard = [
        [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/StarinaVPN_News")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data=f"check_subscription_{action}")],
    ]
    _add_navigation(keyboard, "back_to_main")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== АДМИНИСТРАТИВНЫЕ ==================

def get_admin_topup_keyboard(user_id: int, amount: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для администратора при заявке на пополнение.
    
    Args:
        user_id: ID пользователя
        amount: Сумма пополнения
    """
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Пополнить", callback_data=f"admin_add_balance_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_payment_{user_id}_{amount}"),
        ],
        [InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий администратора над пользователем."""
    keyboard = [
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data=f"admin_topup_{user_id}")],
        [InlineKeyboardButton(text="➖ Списать баланс", callback_data=f"admin_withdraw_{user_id}")],
        [InlineKeyboardButton(text="➕ Продлить подписку", callback_data=f"admin_extend_{user_id}")],
        [InlineKeyboardButton(text="🔄 Сменить ключ", callback_data=f"admin_change_key_{user_id}")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_block_{user_id}")],
        [InlineKeyboardButton(text="📊 История операций", callback_data=f"admin_history_{user_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== НАВИГАЦИЯ ==================
# Все кнопки "Назад" и "Закрыть" без эмодзи по ТЗ

def get_back_keyboard(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад (без эмодзи)."""
    keyboard = [[InlineKeyboardButton(text="Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_close_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой закрыть (без эмодзи)."""
    keyboard = [[InlineKeyboardButton(text="Закрыть", callback_data="close_message")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_and_close_keyboard(back_callback: str = "back_to_main") -> InlineKeyboardMarkup:
    """Клавиатура с кнопками назад и закрыть (без эмодзи)."""
    keyboard = [
        [
            InlineKeyboardButton(text="Назад", callback_data=back_callback),
            InlineKeyboardButton(text="Закрыть", callback_data="close_message"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в главное меню."""
    keyboard = [[InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_navigation_keyboard() -> InlineKeyboardMarkup:
    """Универсальная клавиатура навигации."""
    keyboard = [
        [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="go_to_keys")],
        [InlineKeyboardButton(text="📊 Профиль", callback_data="go_to_profile")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== УСТАРЕВШИЕ ФУНКЦИИ (для совместимости) ==================

def get_key_keyboard() -> InlineKeyboardMarkup:
    """Устаревшая функция - используйте get_keys_keyboard."""
    keyboard = [
        [InlineKeyboardButton(text="📋 Скопировать ключ", callback_data="copy_key")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main"), 
         InlineKeyboardButton(text="Закрыть", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_regenerate_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения смены ключа."""
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, сменить ключ", callback_data="confirm_regenerate")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_regenerate")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

"""
Inline-клавиатуры для администратора.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.models import Server, User


def get_admin_user_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура управления пользователем."""
    keyboard = [
        [
            InlineKeyboardButton(text="💰 Пополнить баланс", callback_data=f"admin_add_balance_{user_id}")
        ],
        [
            InlineKeyboardButton(text="➕ Продлить подписку", callback_data=f"admin_extend_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Сменить ключ", callback_data=f"admin_reset_key_{user_id}")
        ],
        [
            InlineKeyboardButton(text="📊 История операций", callback_data=f"admin_history_{user_id}")
        ],
        [
            InlineKeyboardButton(text="➖ Заблокировать", callback_data=f"admin_block_{user_id}")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_confirm_keyboard(action: str, user_id: int, amount: int = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия админа."""
    if amount:
        confirm_data = f"admin_confirm_{action}_{amount}_{user_id}"
    else:
        confirm_data = f"admin_confirm_{action}_{user_id}"
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_servers_keyboard(servers: list[Server]) -> InlineKeyboardMarkup:
    """Клавиатура управления серверами."""
    keyboard = []
    
    for server in servers:
        status = "✅" if server.is_active else "❌"
        text = f"{status} {server.flag} {server.name}"
        
        keyboard.append([
            InlineKeyboardButton(text=text, callback_data=f"admin_server_{server.id}")
        ])
    
    keyboard.extend([
        [InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server")],
        [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="admin_check_servers")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_server_keyboard(server_id: int) -> InlineKeyboardMarkup:
    """Клавиатура управления конкретным сервером."""
    keyboard = [
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_edit_server_{server_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Перезагрузить", callback_data=f"admin_restart_server_{server_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_delete_server_{server_id}")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_servers")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_mailing_keyboard(users_count: int) -> InlineKeyboardMarkup:
    """Клавиатура рассылки."""
    keyboard = [
        [
            InlineKeyboardButton(text=f"✅ Отправить всем ({users_count})", callback_data="admin_send_all")
        ],
        [
            InlineKeyboardButton(text="🔁 Отправить тест себе", callback_data="admin_send_test")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    keyboard = [
        [
            InlineKeyboardButton(text="✏️ Изменить тарифы", callback_data="admin_edit_prices")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить пробный период", callback_data="admin_edit_trial")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить контакты", callback_data="admin_edit_contacts")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить реферальный бонус", callback_data="admin_edit_referral")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад' для админа."""
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_block_keyboard(user_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    """Клавиатура блокировки/разблокировки пользователя."""
    if is_blocked:
        keyboard = [
            [InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin_unblock_{user_id}")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_block_{user_id}")]
        ]
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

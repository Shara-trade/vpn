"""
Запросы к базе данных для работы с пользователями, серверами и транзакциями.
"""

import time
from datetime import datetime
from typing import Optional, List, Dict
from database.db import db


# ================== КЭШ ==================

_cache = {
    "servers": {"data": None, "expires": 0},
    "tariffs": {"data": None, "expires": 0},
    "settings": {"data": {}, "expires": 0}
}
CACHE_TTL = 60  # секунд


async def invalidate_cache():
    """Сброс кэша (вызывать при изменении данных)."""
    _cache["servers"]["data"] = None
    _cache["tariffs"]["data"] = None
    _cache["settings"]["data"] = {}


# ================== ПОЛЬЗОВАТЕЛИ ==================

async def create_user(
    user_id: int,
    full_name: str,
    username: Optional[str] = None,
    referral_code: str = None
) -> int:
    """
    Создание нового пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        full_name: Имя пользователя
        username: Telegram username
        referral_code: Реферальный код
        
    Returns:
        ID созданной записи
    """
    return await db.execute(
        """
        INSERT INTO users (user_id, username, full_name, referral_code, last_activity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, username, full_name, referral_code, datetime.utcnow())
    )


async def get_user(user_id: int) -> Optional[Dict]:
    """
    Получение пользователя по Telegram ID.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Словарь с данными пользователя или None
    """
    return await db.fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )


async def get_user_by_username(username: str) -> Optional[Dict]:
    """
    Получение пользователя по username.
    
    Args:
        username: Telegram username
        
    Returns:
        Словарь с данными пользователя или None
    """
    # Убираем @ если есть
    username = username.lstrip("@")
    return await db.fetchone(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )


async def update_user_activity(user_id: int) -> None:
    """
    Обновление времени последней активности пользователя.
    
    Args:
        user_id: Telegram ID пользователя
    """
    await db.execute(
        "UPDATE users SET last_activity = ? WHERE user_id = ?",
        (datetime.utcnow(), user_id)
    )


async def update_user_balance(user_id: int, amount: int) -> int:
    """
    Обновление баланса пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        amount: Сумма для добавления (может быть отрицательной)
        
    Returns:
        Новый баланс
    """
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    
    user = await get_user(user_id)
    return user["balance"] if user else 0


async def set_user_server(user_id: int, server_id: int) -> None:
    """
    Установка сервера для пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        server_id: ID сервера
    """
    await db.execute(
        "UPDATE users SET server_id = ? WHERE user_id = ?",
        (server_id, user_id)
    )


async def set_user_key(user_id: int, key: str, key_uuid: str) -> None:
    """
    Установка ключа для пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        key: VLESS ключ
        key_uuid: UUID ключа
    """
    await db.execute(
        "UPDATE users SET current_key = ?, key_uuid = ? WHERE user_id = ?",
        (key, key_uuid, user_id)
    )


async def set_user_expires(user_id: int, expires_at: datetime) -> None:
    """
    Установка даты истечения подписки.
    
    Args:
        user_id: Telegram ID пользователя
        expires_at: Дата истечения
    """
    await db.execute(
        "UPDATE users SET expires_at = ?, status = 'active' WHERE user_id = ?",
        (expires_at, user_id)
    )


async def set_user_status(user_id: int, status: str) -> None:
    """
    Установка статуса пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        status: Новый статус
    """
    await db.execute(
        "UPDATE users SET status = ? WHERE user_id = ?",
        (status, user_id)
    )


async def set_trial_used(user_id: int) -> None:
    """
    Отметка о использовании пробного периода.
    
    Args:
        user_id: Telegram ID пользователя
    """
    await db.execute(
        "UPDATE users SET trial_used = 1, status = 'trial' WHERE user_id = ?",
        (user_id,)
    )


async def get_expiring_users(days: int = 3) -> List[Dict]:
    """
    Получение пользователей с истекающей подпиской.
    
    Args:
        days: Количество дней до истечения
        
    Returns:
        Список пользователей
    """
    return await db.fetchall(
        """
        SELECT * FROM users 
        WHERE expires_at BETWEEN datetime('now') AND datetime('now', ?)
        AND status = 'active'
        """,
        (f"+{days} days",)
    )


async def get_expired_users() -> List[Dict]:
    """
    Получение пользователей с истекшей подпиской.
    
    Returns:
        Список пользователей
    """
    return await db.fetchall(
        """
        SELECT * FROM users 
        WHERE expires_at < datetime('now') 
        AND status = 'active'
        """
    )


async def get_all_users() -> List[Dict]:
    """Получение всех пользователей."""
    return await db.fetchall("SELECT * FROM users ORDER BY registered_at DESC")


async def get_users_count() -> int:
    """Получение общего количества пользователей."""
    return await db.fetchval("SELECT COUNT(*) FROM users")


async def get_active_users_today() -> int:
    """Получение количества активных сегодня пользователей."""
    return await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE date(last_activity) = date('now')"
    )


async def get_new_users_today() -> int:
    """Получение количества новых пользователей за сегодня."""
    return await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE date(registered_at) = date('now')"
    )


# ================== СЕРВЕРЫ ==================

async def create_server(
    name: str,
    country_code: str,
    domain: str,
    ip: str,
    api_url: str,
    api_username: str,
    api_password: str,
    port: int = 443,
    inbound_id: int = 1,
    is_trial: bool = False
) -> int:
    """
    Создание нового сервера.
    
    Returns:
        ID созданного сервера
    """
    return await db.execute(
        """
        INSERT INTO servers (
            name, country_code, domain, ip, api_url, 
            api_username, api_password, port, inbound_id, is_trial
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, country_code, domain, ip, api_url, 
         api_username, api_password, port, inbound_id, is_trial)
    )


async def get_server(server_id: int) -> Optional[Dict]:
    """Получение сервера по ID."""
    return await db.fetchone(
        "SELECT * FROM servers WHERE id = ?",
        (server_id,)
    )


async def get_server_by_code(code: str) -> Optional[Dict]:
    """Получение сервера по коду (ams, fra, etc)."""
    # Для простоты используем первые буквы названия
    return await db.fetchone(
        "SELECT * FROM servers WHERE is_active = 1 LIMIT 1"
    )


async def get_active_servers() -> List[Dict]:
    """Получение всех активных серверов."""
    return await db.fetchall(
        "SELECT * FROM servers WHERE is_active = 1 ORDER BY name"
    )


async def get_active_servers_cached() -> List[Dict]:
    """Получение активных серверов с кэшированием."""
    now = time.time()
    
    if (_cache["servers"]["data"] is not None and 
        now < _cache["servers"]["expires"]):
        return _cache["servers"]["data"]
    
    servers = await get_active_servers()
    _cache["servers"]["data"] = servers
    _cache["servers"]["expires"] = now + CACHE_TTL
    
    return servers


async def get_trial_server() -> Optional[Dict]:
    """Получение сервера для пробного периода."""
    server = await db.fetchone(
        "SELECT * FROM servers WHERE is_active = 1 AND is_trial = 1 LIMIT 1"
    )
    if not server:
        # Если нет специального триального сервера, берем первый активный
        server = await db.fetchone(
            "SELECT * FROM servers WHERE is_active = 1 ORDER BY load ASC LIMIT 1"
        )
    return server


async def update_server_load(server_id: int, load: int) -> None:
    """Обновление нагрузки на сервер."""
    await db.execute(
        "UPDATE servers SET load = ? WHERE id = ?",
        (load, server_id)
    )


async def set_server_active(server_id: int, is_active: bool) -> None:
    """Установка активности сервера."""
    await db.execute(
        "UPDATE servers SET is_active = ? WHERE id = ?",
        (is_active, server_id)
    )


async def get_servers_stats() -> List[Dict]:
    """Получение статистики по серверам."""
    return await db.fetchall(
        """
        SELECT s.name, s.country_code, s.is_active, 
               COUNT(u.id) as users_count
        FROM servers s
        LEFT JOIN users u ON s.id = u.server_id
        GROUP BY s.id
        ORDER BY s.name
        """
    )


async def get_servers_with_load() -> List[Dict]:
    """Получение серверов с нагрузкой."""
    return await db.fetchall(
        """
        SELECT s.name, s.country_code, s.is_active, s.load, s.ping,
               COUNT(u.id) as users_count
        FROM servers s
        LEFT JOIN users u ON s.id = u.server_id AND u.status = 'active'
        GROUP BY s.id
        ORDER BY s.name
        """
    )


# ================== ТРАНЗАКЦИИ ==================

async def create_transaction(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: str = None,
    admin_id: int = None
) -> int:
    """
    Создание транзакции.
    
    Args:
        user_id: ID пользователя
        amount: Сумма в копейках
        transaction_type: Тип (payment, purchase, referral, admin)
        description: Описание
        admin_id: ID администратора (для операций admin)
        
    Returns:
        ID транзакции
    """
    return await db.execute(
        """
        INSERT INTO transactions (user_id, amount, type, description, admin_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, transaction_type, description, admin_id)
    )
    

async def get_user_transactions(user_id: int, limit: int = 10) -> List[Dict]:
    """
    Получение транзакций пользователя.
    
    Args:
        user_id: ID пользователя
        limit: Ограничение количества
        
    Returns:
        Список транзакций
    """
    return await db.fetchall(
        """
        SELECT * FROM transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        """,
        (user_id, limit)
    )


async def get_month_sales() -> int:
    """Получение суммы продаж за месяц."""
    return await db.fetchval(
        """
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'purchase' 
        AND datetime(created_at) >= datetime('now', '-30 days')
        """
    ) or 0


# ================== ТАРИФЫ ==================

async def get_tariffs() -> List[Dict]:
    """Получение всех активных тарифов."""
    return await db.fetchall(
        "SELECT * FROM tariffs WHERE is_active = 1 ORDER BY months"
    )


async def get_tariffs_cached() -> List[Dict]:
    """Получение тарифов с кэшированием."""
    now = time.time()
    
    if (_cache["tariffs"]["data"] is not None and 
        now < _cache["tariffs"]["expires"]):
        return _cache["tariffs"]["data"]
    
    tariffs = await get_tariffs()
    _cache["tariffs"]["data"] = tariffs
    _cache["tariffs"]["expires"] = now + CACHE_TTL
    
    return tariffs


async def get_tariff(tariff_id: int) -> Optional[Dict]:
    """Получение тарифа по ID."""
    return await db.fetchone(
        "SELECT * FROM tariffs WHERE id = ?",
        (tariff_id,)
    )


async def update_tariff_price(tariff_id: int, price: int) -> None:
    """Обновление цены тарифа."""
    await db.execute(
        "UPDATE tariffs SET price = ? WHERE id = ?",
        (price, tariff_id)
    )


# ================== РЕФЕРАЛЫ ==================

async def create_referral(referrer_id: int, referral_id: int) -> int:
    """Создание реферальной связи."""
    return await db.execute(
        """
        INSERT INTO referrals (referrer_id, referral_id)
        VALUES (?, ?)
        """,
        (referrer_id, referral_id)
    )


async def get_referral_stats(user_id: int) -> Dict:
    """
    Получение статистики рефералов пользователя.
    
    Returns:
        Словарь с количеством рефералов и заработком
    """
    stats = await db.fetchone(
        """
        SELECT 
            COUNT(*) as referrals_count,
            COALESCE(SUM(
                CASE WHEN bonus_paid = 1 THEN 0 ELSE 1 END
            ), 0) as unpaid_count
        FROM referrals 
        WHERE referrer_id = ?
        """,
        (user_id,)
    )
    
    user = await get_user(user_id)
    
    return {
        "referrals_count": stats["referrals_count"] if stats else 0,
        "referral_earnings": user["referral_earnings"] if user else 0,
    }


async def set_referral_bonus_paid(referral_id: int) -> None:
    """Отметка о выплате реферального бонуса."""
    await db.execute(
        "UPDATE referrals SET bonus_paid = 1 WHERE referral_id = ?",
        (referral_id,)
    )


# ================== НАСТРОЙКИ ==================

async def get_setting(key: str) -> Optional[str]:
    """Получение настройки по ключу."""
    return await db.fetchval(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )


async def update_setting(key: str, value: str) -> None:
    """Обновление настройки."""
    await db.execute(
        "UPDATE settings SET value = ? WHERE key = ?",
        (value, key)
    )


# ================== СТАТИСТИКА ==================

async def get_total_balance() -> int:
    """Получение общего баланса всех пользователей."""
    return await db.fetchval("SELECT COALESCE(SUM(balance), 0) FROM users") or 0


async def get_avg_check() -> int:
    """Получение среднего чека."""
    return await db.fetchval(
        """
        SELECT COALESCE(AVG(amount), 0) FROM transactions 
        WHERE type = 'purchase'
        """
    ) or 0

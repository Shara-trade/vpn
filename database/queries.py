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
CACHE_TTL = 300  # секунд


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


async def add_referral_earnings(user_id: int, amount: int) -> None:
    """
    Добавление реферальных заработков пользователю.
    
    Args:
        user_id: Telegram ID пользователя
        amount: Сумма в копейках
    """
    await db.execute(
        "UPDATE users SET referral_earnings = referral_earnings + ? WHERE user_id = ?",
        (amount, user_id)
    )


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
    from loguru import logger
    logger.info(f"[DB] Установка статуса '{status}' для пользователя {user_id}")
    
    result = await db.execute(
        "UPDATE users SET status = ? WHERE user_id = ?",
        (status, user_id)
    )
    logger.debug(f"[DB] Результат UPDATE: lastrowid={result}")

    # Проверяем, что статус действительно изменился
    user = await get_user(user_id)
    if user:
        logger.info(f"[DB] Проверка: статус пользователя {user_id} = {user.get('status')}")
    else:
        logger.warning(f"[DB] Пользователь {user_id} не найден после UPDATE!")
    

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


async def has_used_trial(user_id: int) -> bool:
    """
    Проверка, использовал ли пользователь пробный период.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        True если пробный период уже использован
    """
    user = await get_user(user_id)
    return bool(user and user.get("trial_used", 0) == 1)


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


async def get_tariff_by_days(days: int) -> Optional[Dict]:
    """Получение тарифа по количеству дней."""
    return await db.fetchone(
        "SELECT * FROM tariffs WHERE days = ? AND is_active = 1",
        (days,)
    )


async def update_tariff_price(tariff_id: int, price: int) -> None:
    """Обновление цены тарифа."""
    await db.execute(
        "UPDATE tariffs SET price = ? WHERE id = ?",
        (price, tariff_id)
    )


# ================== РЕФЕРАЛЫ ==================
# Обновлено: бонус начисляется при КАЖДОМ пополнении реферала (не только первом)

async def create_referral(referrer_id: int, referral_id: int) -> int:
    """Создание реферальной связи."""
    return await db.execute(
        """
        INSERT INTO referrals (referrer_id, referral_id)
        VALUES (?, ?)
        """,
        (referrer_id, referral_id)
    )
    

async def get_referral_by_referral_id(referral_id: int) -> Optional[Dict]:
    """Получение реферальной связи по ID приглашенного."""
    return await db.fetchone(
        "SELECT * FROM referrals WHERE referral_id = ?",
        (referral_id,)
    )


async def get_referral_stats(user_id: int) -> Dict:
    """
    Получение статистики рефералов пользователя.
    
    Returns:
        Словарь с количеством рефералов и заработком
    """
    stats = await db.fetchone(
        """
        SELECT COUNT(*) as referrals_count
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


async def get_referrals_list(user_id: int) -> List[Dict]:
    """Получение списка рефералов пользователя."""
    return await db.fetchall(
        """
        SELECT r.*, u.username, u.full_name, u.registered_at
        FROM referrals r
        JOIN users u ON r.referral_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
        """,
        (user_id,)
    )


# ================== НАСТРОЙКИ ==================

async def get_setting(key: str) -> Optional[str]:
    """Получение настройки по ключу."""
    return await db.fetchval(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )


async def get_setting_int(key: str, default: int = 0) -> int:
    """Получение настройки как целого числа."""
    value = await get_setting(key)
    if value:
        try:
            return int(value)
        except ValueError:
            pass
    return default


async def update_setting(key: str, value: str) -> None:
    """Обновление настройки."""
    await db.execute(
        "UPDATE settings SET value = ? WHERE key = ?",
        (value, key)
    )


async def get_referral_settings() -> Dict:
    """
    Получение настроек реферальной системы.
    
    Returns:
        Словарь с referral_bonus_percent и referral_min_topup
    """
    return {
        "bonus_percent": await get_setting_int("referral_bonus_percent", 15),
        "min_topup": await get_setting_int("referral_min_topup", 100),
    }


async def get_min_topup() -> int:
    """Получение минимальной суммы пополнения."""
    return await get_setting_int("min_topup", 50)


async def check_channel_subscription(bot, user_id: int) -> bool:
    """
    Проверка подписки пользователя на новостной канал.
    
    Args:
        bot: Экземпляр бота
        user_id: Telegram ID пользователя
        
    Returns:
        True если подписан или проверка невозможна
    """
    try:
        from utils.constants import NEWS_CHANNEL
        if not NEWS_CHANNEL:
            return True
        
        channel = NEWS_CHANNEL.replace("@", "")
        member = await bot.get_chat_member(f"@{channel}", user_id)
        
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        from loguru import logger
        logger.warning(f"Не удалось проверить подписку: {e}")
        # Если канал недоступен или ошибка API - разрешаем действие
        return True


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


# ================== КЛЮЧИ ПОЛЬЗОВАТЕЛЕЙ (user_keys) ==================

async def create_user_key(
    user_id: int,
    key: str,
    key_uuid: str,
    server_id: int,
    expires_at: datetime,
    auto_renew: bool = False
) -> int:
    """
    Создание нового ключа пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        key: VLESS ключ
        key_uuid: UUID ключа
        server_id: ID сервера
        expires_at: Дата истечения
        auto_renew: Автопродление
        
    Returns:
        ID созданного ключа
    """
    return await db.execute(
        """
        INSERT INTO user_keys (user_id, key, key_uuid, server_id, expires_at, auto_renew)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, key, key_uuid, server_id, expires_at, auto_renew)
    )


async def get_user_keys(user_id: int, active_only: bool = True) -> List[Dict]:
    """
    Получение всех ключей пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        active_only: Только активные ключи
        
    Returns:
        Список ключей
    """
    if active_only:
        return await db.fetchall(
            """
            SELECT uk.*, s.name as server_name, s.country_code, s.domain
            FROM user_keys uk
            JOIN servers s ON uk.server_id = s.id
            WHERE uk.user_id = ? AND uk.is_active = 1
            ORDER BY uk.created_at DESC
            """,
            (user_id,)
        )
    return await db.fetchall(
        """
        SELECT uk.*, s.name as server_name, s.country_code, s.domain
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        WHERE uk.user_id = ?
        ORDER BY uk.created_at DESC
        """,
        (user_id,)
    )


async def get_user_key(key_id: int) -> Optional[Dict]:
    """Получение ключа по ID."""
    return await db.fetchone(
        """
        SELECT uk.*, s.name as server_name, s.country_code, s.domain, s.api_url, 
               s.api_username, s.api_password, s.port, s.inbound_id
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        WHERE uk.id = ?
        """,
        (key_id,)
    )


async def get_user_keys_count(user_id: int, active_only: bool = True) -> int:
    """Получение количества ключей пользователя."""
    if active_only:
        return await db.fetchval(
            "SELECT COUNT(*) FROM user_keys WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ) or 0
    return await db.fetchval(
        "SELECT COUNT(*) FROM user_keys WHERE user_id = ?",
        (user_id,)
    ) or 0


async def update_key_expires(key_id: int, expires_at: datetime) -> None:
    """Обновление срока действия ключа."""
    await db.execute(
        "UPDATE user_keys SET expires_at = ? WHERE id = ?",
        (expires_at, key_id)
    )


async def set_key_auto_renew(key_id: int, auto_renew: bool) -> None:
    """Установка автопродления для ключа."""
    await db.execute(
        "UPDATE user_keys SET auto_renew = ? WHERE id = ?",
        (auto_renew, key_id)
    )


async def delete_user_key(key_id: int) -> None:
    """Мягкое удаление ключа (установка is_active = 0)."""
    await db.execute(
        "UPDATE user_keys SET is_active = 0 WHERE id = ?",
        (key_id,)
    )


async def get_expiring_keys(hours: int = 12) -> List[Dict]:
    """
    Получение ключей с истекающим сроком для автопродления.
    
    Args:
        hours: За сколько часов до истечения проверять
        
    Returns:
        Список ключей с auto_renew=1 и expires_at < now + hours
    """
    return await db.fetchall(
        """
        SELECT uk.*, s.name as server_name, u.user_id, u.balance, u.username
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        JOIN users u ON uk.user_id = u.user_id
        WHERE uk.auto_renew = 1 
        AND uk.is_active = 1
        AND uk.expires_at <= datetime('now', ?)
        AND uk.expires_at > datetime('now')
        """,
        (f"+{hours} hours",)
    )


async def get_expired_keys() -> List[Dict]:
    """Получение истекших ключей."""
    return await db.fetchall(
        """
        SELECT uk.*, s.name as server_name
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        WHERE uk.expires_at < datetime('now')
        AND uk.is_active = 1
        """
    )


# ================== СЕРВЕРЫ (обновленные функции) ==================

async def select_best_server() -> Optional[Dict]:
    """
    Выбор лучшего сервера по нагрузке.
    
    Returns:
        Сервер с минимальной нагрузкой
    """
    return await db.fetchone(
        """
        SELECT * FROM servers 
        WHERE is_active = 1 
        AND (capacity = 0 OR load < capacity)
        ORDER BY load ASC, ping ASC
        LIMIT 1
        """
    )


async def increment_server_load(server_id: int) -> None:
    """Увеличение нагрузки сервера на 1."""
    await db.execute(
        "UPDATE servers SET load = load + 1 WHERE id = ?",
        (server_id,)
    )


async def decrement_server_load(server_id: int) -> None:
    """Уменьшение нагрузки сервера на 1."""
    await db.execute(
        "UPDATE servers SET load = MAX(0, load - 1) WHERE id = ?",
        (server_id,)
    )


# ================== ЛОГИ ==================

async def add_log(
    category: str,
    action: str,
    user_id: int = None,
    target_user_id: int = None,
    amount: int = None,
    details: dict = None,
    ip: str = None
) -> int:
    """
    Добавление записи в лог.
    
    Args:
        category: Категория (user, payment, subscription, key, server, admin, referral, promocode, error, system)
        action: Действие
        user_id: ID пользователя
        target_user_id: ID целевого пользователя (для админ-действий)
        amount: Сумма в копейках
        details: Дополнительные данные
        ip: IP адрес
    
    Returns:
        ID записи
    """
    import json
    
    details_json = json.dumps(details, ensure_ascii=False) if details else None
    
    return await db.execute(
        """
        INSERT INTO logs (category, action, user_id, target_user_id, amount, details, ip)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (category, action, user_id, target_user_id, amount, details_json, ip)
    )


async def get_logs(
    category: str = None,
    user_id: int = None,
    limit: int = 100,
    offset: int = 0,
    start_date = None,
    end_date = None
) -> List[Dict]:
    """
    Получение логов с фильтрацией.
    
    Args:
        category: Фильтр по категории
        user_id: Фильтр по пользователю
        limit: Лимит записей
        offset: Смещение
        start_date: Начальная дата
        end_date: Конечная дата
    
    Returns:
        Список логов
    """
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    return await db.fetchall(query, tuple(params))


async def get_log_categories() -> List[str]:
    """Получение всех категорий логов."""
    rows = await db.fetchall("SELECT DISTINCT category FROM logs ORDER BY category")
    return [row["category"] for row in rows]


async def delete_old_logs(days: int = 30) -> int:
    """Удаление старых логов."""
    await db.execute(
        "DELETE FROM logs WHERE created_at < datetime('now', ?)",
        (f"-{days} days",)
    )
    return await db.fetchval("SELECT changes()") or 0


# ================== ПРОМОКОДЫ ==================

async def create_promocode(
    code: str,
    type: str,
    value: int,
    max_uses: int = 0,
    expires_at = None,
    created_by: int = None
) -> int:
    """
    Создание промокода.
    
    Args:
        code: Код промокода
        type: Тип (discount_percent, discount_fixed, free_days, balance, subscription_extension)
        value: Значение
        max_uses: Максимальное количество использований (0 = безлимит)
        expires_at: Дата истечения
        created_by: ID создателя
    
    Returns:
        ID промокода
    """
    return await db.execute(
        """
        INSERT INTO promocodes (code, type, value, max_uses, expires_at, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (code.upper(), type, value, max_uses, expires_at, created_by)
    )


async def get_promocode(code: str) -> Optional[Dict]:
    """Получение промокода по коду."""
    return await db.fetchone(
        "SELECT * FROM promocodes WHERE code = ?",
        (code.upper(),)
    )


async def get_all_promocodes(active_only: bool = False) -> List[Dict]:
    """Получение всех промокодов."""
    if active_only:
        return await db.fetchall(
            """
            SELECT * FROM promocodes 
            WHERE is_active = 1 
            AND (expires_at IS NULL OR expires_at > datetime('now'))
            ORDER BY created_at DESC
            """
        )
    return await db.fetchall("SELECT * FROM promocodes ORDER BY created_at DESC")


async def activate_promocode(user_id: int, code: str):
    """
    Активация промокода пользователем.
    
    Returns:
        Кортеж (успех, сообщение, данные промокода)
    """
    from datetime import datetime
    from utils.helpers import parse_datetime
    
    promocode = await get_promocode(code)
    
    if not promocode:
        return False, "❌ Промокод не найден", None
    
    if not promocode["is_active"]:
        return False, "❌ Промокод деактивирован", None
    
    # Проверка срока действия
    if promocode.get("expires_at"):
        expires_dt = parse_datetime(promocode["expires_at"])
        if expires_dt and expires_dt < datetime.utcnow():
            return False, "❌ Срок действия промокода истек", None
    
    # Проверка лимита использований
    if promocode["max_uses"] > 0 and promocode["used_count"] >= promocode["max_uses"]:
        return False, "❌ Промокод больше недействителен (исчерпан лимит)", None
    
    # Проверка, не использовал ли пользователь этот промокод
    usage = await db.fetchone(
        "SELECT id FROM promocode_usages WHERE promocode_id = ? AND user_id = ?",
        (promocode["id"], user_id)
    )
    if usage:
        return False, "❌ Вы уже использовали этот промокод", None
    
    return True, "✅ Промокод активирован!", promocode


async def apply_promocode(user_id: int, promocode: Dict) -> bool:
    """
    Применение промокода к пользователю.
    
    Args:
        user_id: ID пользователя
        promocode: Данные промокода
    
    Returns:
        True если успешно
    """
    from datetime import datetime, timedelta
    from utils.helpers import parse_datetime
    from services.xui_api import XuiService
    
    # Записываем использование
    await db.execute(
        """
        INSERT INTO promocode_usages (promocode_id, user_id)
        VALUES (?, ?)
        """,
        (promocode["id"], user_id)
    )
    
    # Обновляем счетчик использований
    await db.execute(
        "UPDATE promocodes SET used_count = used_count + 1 WHERE id = ?",
        (promocode["id"],)
    )
    
    # Применяем эффект
    if promocode["type"] == "balance":
        await update_user_balance(user_id, promocode["value"])
        await create_transaction(
            user_id=user_id,
            amount=promocode["value"],
            transaction_type="promocode",
            description=f"Активация промокода: {promocode['code']}"
        )
    
    elif promocode["type"] in ["free_days", "subscription_extension"]:
        user = await get_user(user_id)
        expires_dt = parse_datetime(user.get("expires_at"))
        
        if expires_dt and expires_dt > datetime.utcnow():
            new_expires = expires_dt + timedelta(days=promocode["value"])
        else:
            new_expires = datetime.utcnow() + timedelta(days=promocode["value"])
            
            # Если нет ключа, создаем
            if not user.get("current_key"):
                server = await get_trial_server()
                if server:
                    xui = XuiService(server)
                    key_data = await xui.create_client(user_id, days=promocode["value"])
                    if key_data:
                        await set_user_key(user_id, key_data["key"], key_data["uuid"])
                        await set_user_server(user_id, server["id"])
        
        await set_user_expires(user_id, new_expires)
        await set_user_status(user_id, "active")
        
        await create_transaction(
            user_id=user_id,
            amount=0,
            transaction_type="promocode",
            description=f"{'Бесплатные дни' if promocode['type'] == 'free_days' else 'Продление'}: {promocode['value']} дней (промокод: {promocode['code']})"
        )
    
    # Добавляем в логи
    await add_log(
        category="promocode",
        action="activated",
        user_id=user_id,
        details={
            "promocode": promocode["code"],
            "type": promocode["type"],
            "value": promocode["value"]
        }
    )
    
    return True


async def deactivate_promocode(promocode_id: int) -> bool:
    """Деактивация промокода."""
    await db.execute(
        "UPDATE promocodes SET is_active = 0 WHERE id = ?",
        (promocode_id,)
    )
    return True


async def get_user_keys(user_id: int, active_only: bool = True) -> List[Dict]:
    """
    Получение всех ключей пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        active_only: Только активные ключи
        
    Returns:
        Список ключей
    """
    if active_only:
        return await db.fetchall(
            """
            SELECT uk.*, s.name as server_name, s.domain as server_domain, s.country_code
            FROM user_keys uk
            JOIN servers s ON uk.server_id = s.id
            WHERE uk.user_id = ? AND uk.is_active = 1
            ORDER BY uk.created_at DESC
            """,
            (user_id,)
        )
    return await db.fetchall(
        """
        SELECT uk.*, s.name as server_name, s.domain as server_domain, s.country_code
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        WHERE uk.user_id = ?
        ORDER BY uk.created_at DESC
        """,
        (user_id,)
    )


async def get_user_key(key_id: int) -> Optional[Dict]:
    """
    Получение ключа по ID.
    
    Args:
        key_id: ID ключа
        
    Returns:
        Данные ключа или None
    """
    return await db.fetchone(
        """
        SELECT uk.*, s.name as server_name, s.domain as server_domain, s.country_code
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        WHERE uk.id = ?
        """,
        (key_id,)
    )


async def get_user_key_by_uuid(key_uuid: str) -> Optional[Dict]:
    """
    Получение ключа по UUID.
    
    Args:
        key_uuid: UUID ключа
        
    Returns:
        Данные ключа или None
    """
    return await db.fetchone(
        """
        SELECT uk.*, s.name as server_name, s.domain as server_domain
        FROM user_keys uk
        JOIN servers s ON uk.server_id = s.id
        WHERE uk.key_uuid = ?
        """,
        (key_uuid,)
    )


async def update_key_expires(key_id: int, expires_at: datetime) -> None:
    """
    Обновление даты истечения ключа.
    
    Args:
        key_id: ID ключа
        expires_at: Новая дата истечения
    """
    await db.execute(
        "UPDATE user_keys SET expires_at = ? WHERE id = ?",
        (expires_at, key_id)
    )


async def set_key_auto_renew(key_id: int, auto_renew: bool) -> None:
    """
    Установка автопродления для ключа.
    
    Args:
        key_id: ID ключа
        auto_renew: Включить/выключить автопродление
    """
    await db.execute(
        "UPDATE user_keys SET auto_renew = ? WHERE id = ?",
        (auto_renew, key_id)
    )


async def delete_user_key(key_id: int) -> None:
    """
    Удаление ключа (пометка как неактивный).
    
    Args:
        key_id: ID ключа
    """
    await db.execute(
        "UPDATE user_keys SET is_active = 0 WHERE id = ?",
        (key_id,)
    )


async def get_active_keys_count(user_id: int) -> int:
    """
    Получение количества активных ключей пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Количество активных ключей
    """
    return await db.fetchval(
        "SELECT COUNT(*) FROM user_keys WHERE user_id = ? AND is_active = 1",
        (user_id,)
    ) or 0


async def get_keys_for_auto_renew() -> List[Dict]:
    """
    Получение ключей для автопродления.
    Ключи с auto_renew=1 и expires_at < now + 12 часов.
    
    Returns:
        Список ключей для продления
    """
    from datetime import timedelta
    check_time = datetime.utcnow() + timedelta(hours=12)
    
    return await db.fetchall(
        """
        SELECT uk.*, u.balance, u.user_id as uid
        FROM user_keys uk
        JOIN users u ON uk.user_id = u.user_id
        WHERE uk.auto_renew = 1 
        AND uk.is_active = 1
        AND uk.expires_at <= ?
        """,
        (check_time,)
    )


async def get_expiring_keys_by_days(days: int = 3) -> List[Dict]:
    """
    Получение ключей с истекающей подпиской.
    
    Args:
        days: Количество дней до истечения
        
    Returns:
        Список ключей
    """
    return await db.fetchall(
        """
        SELECT uk.*, u.user_id
        FROM user_keys uk
        JOIN users u ON uk.user_id = u.user_id
        WHERE uk.expires_at BETWEEN datetime('now') AND datetime('now', ?)
        AND uk.is_active = 1
        """,
        (f"+{days} days",)
    )


async def get_expired_keys() -> List[Dict]:
    """
    Получение истекших ключей.
    
    Returns:
        Список ключей
    """
    return await db.fetchall(
        """
        SELECT uk.*, u.user_id
        FROM user_keys uk
        JOIN users u ON uk.user_id = u.user_id
        WHERE uk.expires_at < datetime('now') 
        AND uk.is_active = 1
        """
    )


async def update_key_uuid(key_id: int, new_key: str, new_uuid: str) -> None:
    """
    Обновление ключа и UUID (при смене ключа).
    
    Args:
        key_id: ID ключа
        new_key: Новый VLESS ключ
        new_uuid: Новый UUID
    """
    await db.execute(
        "UPDATE user_keys SET key = ?, key_uuid = ? WHERE id = ?",
        (new_key, new_uuid, key_id)
    )


# ================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПРОМОКОДОВ ==================

async def get_promocode_usage(promocode_id: int, user_id: int) -> Optional[Dict]:
    """Проверка использования промокода пользователем."""
    return await db.fetchone(
        "SELECT * FROM promocode_usages WHERE promocode_id = ? AND user_id = ?",
        (promocode_id, user_id)
    )


async def create_promocode_usage(promocode_id: int, user_id: int) -> int:
    """Запись использования промокода."""
    return await db.execute(
        "INSERT INTO promocode_usages (promocode_id, user_id) VALUES (?, ?)",
        (promocode_id, user_id)
    )


async def increment_promocode_usage(promocode_id: int) -> None:
    """Увеличение счетчика использований промокода."""
    await db.execute(
        "UPDATE promocodes SET used_count = used_count + 1 WHERE id = ?",
        (promocode_id,)
    )


# ================== ОБНОВЛЕННЫЕ ФУНКЦИИ РЕФЕРАЛОВ ==================

async def get_referrer(user_id: int) -> Optional[Dict]:
    """""
    Получение реферера пользователя (кто пригласил).
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Данные реферальной связи или None
    """
    return await db.fetchone(
        "SELECT * FROM referrals WHERE referral_id = ?",
        (user_id,)
    )


async def add_referral_earnings(referrer_id: int, amount: int) -> None:
    """""
    Добавление заработка рефереру.
    Бонус начисляется ВСЕГДА (при каждом пополнении реферала).
    
    Args:
        referrer_id: ID пригласившего
        amount: Сумма бонуса в копейках
    """
    await db.execute(
        "UPDATE users SET referral_earnings = referral_earnings + ? WHERE user_id = ?",
        (amount, referrer_id)
    )


async def get_referral_paid_amount(referral_id: int) -> int:
    ""
    Получение
""
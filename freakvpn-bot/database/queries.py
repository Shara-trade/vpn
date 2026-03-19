"""
Запросы к базе данных.
"""
from datetime import datetime, timedelta
from typing import Optional, List
import aiosqlite

from database.db import get_db
from database.models import User, Server, Tariff, Transaction, Referral
from utils.helpers import generate_referral_code


# === USERS ===

async def create_user(
    user_id: int,
    username: Optional[str],
    full_name: str,
    referred_by: Optional[int] = None
) -> User:
    """Создаёт нового пользователя."""
    db = await get_db()
    referral_code = generate_referral_code(user_id)
    
    cursor = await db.execute(
        """
        INSERT INTO users (user_id, username, full_name, referral_code, referred_by, last_activity)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, username, full_name, referral_code, referred_by, datetime.now())
    )
    await db.commit()
    
    return await get_user_by_id(user_id)


async def get_user_by_id(user_id: int) -> Optional[User]:
    """Получает пользователя по Telegram ID."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = await cursor.fetchone()
    
    return _row_to_user(row) if row else None


async def get_user_by_username(username: str) -> Optional[User]:
    """Получает пользователя по username."""
    db = await get_db()
    
    if username.startswith("@"):
        username = username[1:]
    
    cursor = await db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    row = await cursor.fetchone()
    
    return _row_to_user(row) if row else None


async def get_user_by_referral_code(referral_code: str) -> Optional[User]:
    """Получает пользователя по реферальному коду."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM users WHERE referral_code = ?",
        (referral_code,)
    )
    row = await cursor.fetchone()
    
    return _row_to_user(row) if row else None


async def update_user(user_id: int, **kwargs) -> bool:
    """Обновляет данные пользователя."""
    if not kwargs:
        return False
    
    db = await get_db()
    set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
    values = list(kwargs.values()) + [user_id]
    
    await db.execute(
        f"UPDATE users SET {set_clause} WHERE user_id = ?",
        values
    )
    await db.commit()
    
    return True


async def update_last_activity(user_id: int):
    """Обновляет время последней активности."""
    db = await get_db()
    await db.execute(
        "UPDATE users SET last_activity = ? WHERE user_id = ?",
        (datetime.now(), user_id)
    )
    await db.commit()
    

async def get_active_users() -> List[User]:
    """Получает всех активных пользователей."""
    db = await get_db()
    
    cursor = await db.execute(
        """
        SELECT * FROM users 
        WHERE status != 'blocked' 
        AND expires_at > ?
        """,
        (datetime.now(),)
    )
    rows = await cursor.fetchall()
    
    return [_row_to_user(row) for row in rows]


async def get_expiring_users(days: int = 3) -> List[User]:
    """Получает пользователей, у которых истекает подписка."""
    db = await get_db()
    
    now = datetime.now()
    until = now + timedelta(days=days)
    
    cursor = await db.execute(
        """
        SELECT * FROM users 
        WHERE status = 'active' 
        AND expires_at BETWEEN ? AND ?
        """,
        (now, until)
    )
    rows = await cursor.fetchall()
    
    return [_row_to_user(row) for row in rows]


async def get_expired_users() -> List[User]:
    """Получает пользователей с истекшей подпиской."""
    db = await get_db()
    
    cursor = await db.execute(
        """
        SELECT * FROM users 
        WHERE status = 'active' 
        AND expires_at < ?
        """,
        (datetime.now(),)
    )
    rows = await cursor.fetchall()
    
    return [_row_to_user(row) for row in rows]


async def get_all_users() -> List[User]:
    """Получает всех пользователей."""
    db = await get_db()
    
    cursor = await db.execute("SELECT * FROM users ORDER BY registered_at DESC")
    rows = await cursor.fetchall()
    
    return [_row_to_user(row) for row in rows]


def _row_to_user(row: aiosqlite.Row) -> User:
    """Конвертирует строку БД в объект User."""
    return User(
        id=row["id"],
        user_id=row["user_id"],
        username=row["username"],
        full_name=row["full_name"],
        registered_at=datetime.fromisoformat(row["registered_at"]) if row["registered_at"] else None,
        status=row["status"],
        expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        balance=row["balance"],
        server_id=row["server_id"],
        current_key=row["current_key"],
        key_uuid=row["key_uuid"],
        referral_code=row["referral_code"],
        referred_by=row["referred_by"],
        referral_earnings=row["referral_earnings"],
        is_admin=bool(row["is_admin"]),
        trial_used=bool(row["trial_used"]),
        last_activity=datetime.fromisoformat(row["last_activity"]) if row["last_activity"] else None,
        total_traffic=row["total_traffic"] or 0
    )


# === SERVERS ===

async def get_server_by_id(server_id: int) -> Optional[Server]:
    """Получает сервер по ID."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM servers WHERE id = ?",
        (server_id,)
    )
    row = await cursor.fetchone()
    
    return _row_to_server(row) if row else None


async def get_active_servers() -> List[Server]:
    """Получает все активные серверы."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM servers WHERE is_active = 1 ORDER BY name"
    )
    rows = await cursor.fetchall()
    
    return [_row_to_server(row) for row in rows]


async def get_trial_server() -> Optional[Server]:
    """Получает сервер для пробного периода."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM servers WHERE is_active = 1 AND is_trial = 1 LIMIT 1"
    )
    row = await cursor.fetchone()
    
    return _row_to_server(row) if row else None


async def create_server(
    name: str,
    country_code: str,
    domain: str,
    ip: str,
    api_url: str,
    api_username: str,
    api_password: str,
    port: int = 443,
    is_trial: bool = False,
    inbound_id: int = 1
) -> Server:
    """Создаёт новый сервер."""
    db = await get_db()
    
    cursor = await db.execute(
        """
        INSERT INTO servers (name, country_code, domain, ip, api_url, api_username, api_password, port, is_trial, inbound_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, country_code, domain, ip, api_url, api_username, api_password, port, is_trial, inbound_id)
    )
    await db.commit()
    
    return await get_server_by_id(cursor.lastrowid)


async def update_server(server_id: int, **kwargs) -> bool:
    """Обновляет данные сервера."""
    if not kwargs:
        return False
    
    db = await get_db()
    set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
    values = list(kwargs.values()) + [server_id]
    
    await db.execute(
        f"UPDATE servers SET {set_clause} WHERE id = ?",
        values
    )
    await db.commit()
    
    return True


async def delete_server(server_id: int) -> bool:
    """Удаляет сервер."""
    db = await get_db()
    
    await db.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    await db.commit()
    
    return True


def _row_to_server(row: aiosqlite.Row) -> Server:
    """Конвертирует строку БД в объект Server."""
    return Server(
        id=row["id"],
        name=row["name"],
        country_code=row["country_code"],
        domain=row["domain"],
        ip=row["ip"],
        api_url=row["api_url"],
        api_username=row["api_username"],
        api_password=row["api_password"],
        port=row["port"],
        is_active=bool(row["is_active"]),
        is_trial=bool(row["is_trial"]),
        inbound_id=row["inbound_id"],
        user_count=row["user_count"],
        ping=row["ping"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
    )


# === TARIFFS ===

async def get_tariffs() -> List[Tariff]:
    """Получает все активные тарифы."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM tariffs WHERE is_active = 1 ORDER BY months"
    )
    rows = await cursor.fetchall()
    
    return [_row_to_tariff(row) for row in rows]


async def get_tariff_by_id(tariff_id: int) -> Optional[Tariff]:
    """Получает тариф по ID."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM tariffs WHERE id = ?",
        (tariff_id,)
    )
    row = await cursor.fetchone()
    
    return _row_to_tariff(row) if row else None


async def get_tariff_by_months(months: int) -> Optional[Tariff]:
    """Получает тариф по количеству месяцев."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM tariffs WHERE months = ? AND is_active = 1",
        (months,)
    )
    row = await cursor.fetchone()
    
    return _row_to_tariff(row) if row else None


def _row_to_tariff(row: aiosqlite.Row) -> Tariff:
    """Конвертирует строку БД в объект Tariff."""
    return Tariff(
        id=row["id"],
        name=row["name"],
        months=row["months"],
        price=row["price"],
        is_active=bool(row["is_active"])
    )


# === TRANSACTIONS ===

async def create_transaction(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: Optional[str] = None,
    admin_id: Optional[int] = None
) -> Transaction:
    """Создаёт транзакцию."""
    db = await get_db()
    
    cursor = await db.execute(
        """
        INSERT INTO transactions (user_id, amount, type, description, admin_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, transaction_type, description, admin_id)
    )
    await db.commit()
    
    return await get_transaction_by_id(cursor.lastrowid)


async def get_transaction_by_id(transaction_id: int) -> Optional[Transaction]:
    """Получает транзакцию по ID."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM transactions WHERE id = ?",
        (transaction_id,)
    )
    row = await cursor.fetchone()
    
    return _row_to_transaction(row) if row else None


async def get_user_transactions(user_id: int, limit: int = 20) -> List[Transaction]:
    """Получает транзакции пользователя."""
    db = await get_db()
    
    cursor = await db.execute(
        """
        SELECT * FROM transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        """,
        (user_id, limit)
    )
    rows = await cursor.fetchall()
    
    return [_row_to_transaction(row) for row in rows]


def _row_to_transaction(row: aiosqlite.Row) -> Transaction:
    """Конвертирует строку БД в объект Transaction."""
    return Transaction(
        id=row["id"],
        user_id=row["user_id"],
        amount=row["amount"],
        type=row["type"],
        description=row["description"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        admin_id=row["admin_id"]
    )


# === REFERRALS ===

async def create_referral(referrer_id: int, referral_id: int) -> Referral:
    """Создаёт связь реферала."""
    db = await get_db()
    
    cursor = await db.execute(
        """
        INSERT INTO referrals (referrer_id, referral_id)
        VALUES (?, ?)
        """,
        (referrer_id, referral_id)
    )
    await db.commit()
    
    return await get_referral_by_id(cursor.lastrowid)


async def get_referral_by_id(referral_id: int) -> Optional[Referral]:
    """Получает реферальную связь по ID."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM referrals WHERE id = ?",
        (referral_id,)
    )
    row = await cursor.fetchone()
    
    return _row_to_referral(row) if row else None


async def get_user_referrals(user_id: int) -> List[Referral]:
    """Получает рефералов пользователя."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM referrals WHERE referrer_id = ?",
        (user_id,)
    )
    rows = await cursor.fetchall()
    
    return [_row_to_referral(row) for row in rows]


async def mark_referral_bonus_paid(referral_id: int) -> bool:
    """Отмечает, что бонус за реферала выплачен."""
    db = await get_db()
    
    await db.execute(
        "UPDATE referrals SET bonus_paid = 1 WHERE id = ?",
        (referral_id,)
    )
    await db.commit()
    
    return True


def _row_to_referral(row: aiosqlite.Row) -> Referral:
    """Конвертирует строку БД в объект Referral."""
    return Referral(
        id=row["id"],
        referrer_id=row["referrer_id"],
        referral_id=row["referral_id"],
        bonus_paid=bool(row["bonus_paid"]),
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
    )


# === SETTINGS ===

async def get_setting(key: str) -> Optional[str]:
    """Получает настройку по ключу."""
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )
    row = await cursor.fetchone()
    
    return row["value"] if row else None


async def update_setting(key: str, value: str) -> bool:
    """Обновляет настройку."""
    db = await get_db()
    
    await db.execute(
        "UPDATE settings SET value = ? WHERE key = ?",
        (value, key)
    )
    await db.commit()
    
    return True


# === STATISTICS ===

async def get_stats() -> dict:
    """Получает общую статистику."""
    db = await get_db()
    
    # Всего пользователей
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    total_users = (await cursor.fetchone())[0]
    
    # Активных сегодня
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE date(last_activity) = date('now')"
    )
    active_today = (await cursor.fetchone())[0]
    
    # Новых за сегодня
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE date(registered_at) = date('now')"
    )
    new_today = (await cursor.fetchone())[0]
    
    # Общий баланс
    cursor = await db.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_balance = (await cursor.fetchone())[0]
    
    # Продажи за месяц
    cursor = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'purchase' 
        AND created_at >= date('now', '-30 days')
        """
    )
    month_sales = (await cursor.fetchone())[0]
    
    return {
        "total_users": total_users,
        "active_today": active_today,
        "new_today": new_today,
        "total_balance": total_balance,
        "month_sales": month_sales
    }

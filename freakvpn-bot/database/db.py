"""
Подключение к базе данных.
"""
import aiosqlite
from typing import Optional
from loguru import logger

from config import DATABASE_PATH


_db_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Возвращает соединение с базой данных."""
    global _db_connection
    
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DATABASE_PATH)
        _db_connection.row_factory = aiosqlite.Row
        logger.info(f"Подключено к базе данных: {DATABASE_PATH}")
    
    return _db_connection


async def init_db():
    """Инициализирует базу данных и создаёт таблицы."""
    db = await get_db()
    
    # Таблица пользователей
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'active',
            expires_at DATETIME,
            balance INTEGER NOT NULL DEFAULT 0,
            server_id INTEGER,
            current_key TEXT,
            key_uuid TEXT,
            referral_code TEXT UNIQUE NOT NULL,
            referred_by INTEGER,
            referral_earnings INTEGER NOT NULL DEFAULT 0,
            is_admin BOOLEAN NOT NULL DEFAULT 0,
            trial_used BOOLEAN NOT NULL DEFAULT 0,
            last_activity DATETIME,
            total_traffic INTEGER DEFAULT 0,
            FOREIGN KEY (server_id) REFERENCES servers(id),
            FOREIGN KEY (referred_by) REFERENCES users(user_id)
        )
    """)
    
    # Таблица серверов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country_code TEXT NOT NULL,
            domain TEXT NOT NULL,
            ip TEXT NOT NULL,
            api_url TEXT NOT NULL,
            api_username TEXT NOT NULL,
            api_password TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 443,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_trial BOOLEAN NOT NULL DEFAULT 0,
            inbound_id INTEGER DEFAULT 1,
            user_count INTEGER NOT NULL DEFAULT 0,
            ping INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица транзакций
    await db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            admin_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица тарифов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            months INTEGER NOT NULL,
            price INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    """)
    
    # Таблица рефералов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referral_id INTEGER UNIQUE NOT NULL,
            bonus_paid BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referral_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица настроек
    await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT
        )
    """)
    
    # Таблица рассылок
    await db.execute("""
        CREATE TABLE IF NOT EXISTS mailings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_sent INTEGER DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sent_at DATETIME
        )
    """)
    
    await db.commit()
    
    # Инициализация дефолтных данных
    await _init_default_data(db)
    
    logger.info("Таблицы базы данных созданы")


async def _init_default_data(db: aiosqlite.Connection):
    """Инициализирует дефолтные данные."""
    # Дефолтные тарифы
    tariffs = [
        ("1 месяц", 1, 29900, True),
        ("3 месяца", 3, 79900, True),
        ("6 месяцев", 6, 149900, True),
        ("12 месяцев", 12, 249900, True)
    ]
    
    cursor = await db.execute("SELECT COUNT(*) FROM tariffs")
    count = (await cursor.fetchone())[0]
    
    if count == 0:
        for name, months, price, is_active in tariffs:
            await db.execute(
                "INSERT INTO tariffs (name, months, price, is_active) VALUES (?, ?, ?, ?)",
                (name, months, price, is_active)
            )
        logger.info("Дефолтные тарифы добавлены")
    
    # Дефолтные настройки
    settings = [
        ("trial_days", "3", "Дней пробного периода"),
        ("referral_bonus", "5000", "Реферальный бонус в копейках"),
        ("payment_contact", "@FreakVPN_Shop", "Контакт для оплаты"),
        ("support_contact", "@FreakVPN_Support", "Контакт поддержки")
    ]
    
    cursor = await db.execute("SELECT COUNT(*) FROM settings")
    count = (await cursor.fetchone())[0]
    
    if count == 0:
        for key, value, description in settings:
            await db.execute(
                "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
                (key, value, description)
            )
        logger.info("Дефолтные настройки добавлены")
    
    await db.commit()


async def close_db():
    """Закрывает соединение с базой данных."""
    global _db_connection
    
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("Соединение с базой данных закрыто")

"""
Модели и инициализация таблиц базы данных.
"""

from database.db import db
from loguru import logger
from utils.constants import DEFAULT_TARIFFS


async def init_db() -> None:
    """
    Инициализация базы данных.
    Создание всех таблиц, если они не существуют.
    """
    await db.connect()
    
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
            traffic_used INTEGER NOT NULL DEFAULT 0,
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
            inbound_id INTEGER NOT NULL DEFAULT 1,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_trial BOOLEAN NOT NULL DEFAULT 0,
            load INTEGER NOT NULL DEFAULT 0,
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
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (admin_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица тарифов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            months INTEGER NOT NULL,
            price INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица рефералов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referral_id INTEGER UNIQUE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            bonus_paid BOOLEAN NOT NULL DEFAULT 0,
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
            total_users INTEGER NOT NULL DEFAULT 0,
            sent_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME,
            completed_at DATETIME,
            FOREIGN KEY (admin_id) REFERENCES users(user_id)
        )
    """)
    
    # Инициализация тарифов по умолчанию
    await init_default_tariffs()
    
    # Инициализация настроек по умолчанию
    await init_default_settings()
    
    logger.info("База данных инициализирована успешно")


async def init_default_tariffs() -> None:
    """Инициализация тарифов по умолчанию."""
    existing = await db.fetchone("SELECT COUNT(*) as count FROM tariffs")
    
    if existing and existing["count"] == 0:
        for tariff in DEFAULT_TARIFFS:
            await db.execute(
                """
                INSERT INTO tariffs (name, months, price)
                VALUES (?, ?, ?)
                """,
                (tariff["name"], tariff["months"], tariff["price"])
            )
        logger.info("Тарифы по умолчанию добавлены")


async def init_default_settings() -> None:
    """Инициализация настроек по умолчанию."""
    from config import config
    
    default_settings = [
        ("trial_days", str(config.DEFAULT_TRIAL_DAYS), "Количество дней пробного периода"),
        ("referral_bonus", str(config.DEFAULT_REFERRAL_BONUS), "Бонус за реферала в копейках"),
        ("support_contact", "@FreakVPN_Support", "Контакт поддержки"),
        ("payment_contact", "@FreakVPN_Shop", "Контакт для оплаты"),
    ]
    
    for key, value, description in default_settings:
        existing = await db.fetchone(
            "SELECT id FROM settings WHERE key = ?",
            (key,)
        )
        if not existing:
            await db.execute(
                """
                INSERT INTO settings (key, value, description)
                VALUES (?, ?, ?)
                """,
                (key, value, description)
            )
    
    logger.info("Настройки по умолчанию инициализированы")

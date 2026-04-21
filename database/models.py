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
            FOREIGN KEY (referred_by) REFERENCES users(user_id)
        )
    """)
    
    # Таблица ключей пользователей (поддержка до 5 ключей)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            key_uuid TEXT NOT NULL,
            server_id INTEGER NOT NULL,
            expires_at DATETIME NOT NULL,
            auto_renew BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (server_id) REFERENCES servers(id)
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
            capacity INTEGER NOT NULL DEFAULT 200,
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
            days INTEGER NOT NULL DEFAULT 0,
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
    
    # Таблица логов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            action TEXT NOT NULL,
            user_id INTEGER,
            target_user_id INTEGER,
            amount INTEGER,
            details TEXT,
            ip TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица промокодов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            value INTEGER NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 0,
            used_count INTEGER NOT NULL DEFAULT 0,
            expires_at DATETIME,
            created_by INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(user_id)
        )
    """)
    
    # Таблица активаций промокодов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS promocode_usages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promocode_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            activated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (promocode_id) REFERENCES promocodes(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(promocode_id, user_id)
        )
    """)
    
    # Индексы для оптимизации
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_expires_at ON users(expires_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_keys_user_id ON user_keys(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_keys_expires_at ON user_keys(expires_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_keys_auto_renew ON user_keys(auto_renew)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_servers_is_active ON servers(is_active)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_servers_is_trial ON servers(is_trial)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_servers_load ON servers(load)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(category)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_promocodes_code ON promocodes(code)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_promocode_usages_user_id ON promocode_usages(user_id)")
    
    # Инициализация тарифов по умолчанию
    await init_default_tariffs()
    
    # Инициализация настроек по умолчанию
    await init_default_settings()
    
    logger.info("База данных инициализирована успешно")


async def init_default_tariffs() -> None:
    """Инициализация тарифов по умолчанию."""
    existing = await db.fetchone("SELECT COUNT(*) as count FROM tariffs")
    
    if existing and existing["count"] == 0:
        # Тарифы по ТЗ: пробный, 1 неделя, 1 мес, 3 мес, 6 мес, 12 мес
        default_tariffs = [
            {"name": "Пробный ключ", "months": 0, "days": 3, "price": 0},
            {"name": "1 неделя", "months": 0, "days": 7, "price": 15000},
            {"name": "1 месяц", "months": 1, "days": 30, "price": 29900},
            {"name": "3 месяца", "months": 3, "days": 90, "price": 79900},
            {"name": "6 месяцев", "months": 6, "days": 180, "price": 149900},
            {"name": "12 месяцев", "months": 12, "days": 360, "price": 249900},
        ]
        for tariff in default_tariffs:
            await db.execute(
                """
                INSERT INTO tariffs (name, months, days, price)
                VALUES (?, ?, ?, ?)
                """,
                (tariff["name"], tariff["months"], tariff["days"], tariff["price"])
            )
        logger.info("Тарифы по умолчанию добавлены")
    

async def init_default_settings() -> None:
    """Инициализация настроек по умолчанию."""
    from config import config
    
    default_settings = [
        ("trial_days", str(config.DEFAULT_TRIAL_DAYS), "Количество дней пробного периода"),
        ("referral_bonus_percent", "15", "Процент бонуса пригласившему от пополнения реферала"),
        ("referral_min_topup", "100", "Минимальная сумма пополнения для начисления реферального бонуса (рубли)"),
        ("min_topup", "50", "Минимальная сумма пополнения баланса (рубли)"),
        ("support_contact", "@StarinaVPN_Support_bot", "Контакт поддержки"),
        ("payment_contact", "@StarinaVPN_Shop", "Контакт для оплаты"),
        ("news_channel", "@StarinaVPN_News", "Новостной канал для проверки подписки"),
        ("reviews_channel", "@StarinaVPN_Reviews", "Канал отзывов"),
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

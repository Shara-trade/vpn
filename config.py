"""
Конфигурация бота FreakVPN.
Все настройки загружаются из переменных окружения.
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс конфигурации бота."""
    
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = [
        int(id.strip()) 
        for id in os.getenv("ADMIN_IDS", "").split(",") 
        if id.strip()
    ]
    
    # Пробный период и рефералы
    DEFAULT_TRIAL_DAYS: int = int(os.getenv("DEFAULT_TRIAL_DAYS", "3"))
    DEFAULT_REFERRAL_BONUS: int = int(os.getenv("DEFAULT_REFERRAL_BONUS", "5000"))  # в копейках
    
    # База данных
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "freakvpn.db")
    
    # X-UI настройки
    XUI_DEFAULT_PORT: int = int(os.getenv("XUI_DEFAULT_PORT", "54321"))
    XUI_DEFAULT_PROTOCOL: str = os.getenv("XUI_DEFAULT_PROTOCOL", "vless")
    
    # Системные
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка обязательных настроек."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не указан в .env файле")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не указаны в .env файле")
        return True


# Глобальный экземпляр конфигурации
config = Config()

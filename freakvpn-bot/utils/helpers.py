"""
Вспомогательные функции.
"""
from datetime import datetime
from typing import Optional


def format_balance(kopecks: int) -> str:
    """Конвертирует копейки в рубли и форматирует."""
    return f"{kopecks / 100:,.0f}".replace(",", " ")


def to_kopecks(rubles: int | float) -> int:
    """Конвертирует рубли в копейки."""
    return int(rubles * 100)


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y") -> str:
    """Форматирует datetime в строку."""
    if dt is None:
        return "Не указано"
    return dt.strftime(format_str)


def format_datetime_full(dt: datetime) -> str:
    """Форматирует datetime с временем."""
    if dt is None:
        return "Не указано"
    return dt.strftime("%d.%m.%Y %H:%M")


def generate_referral_code(user_id: int) -> str:
    """Генерирует реферальный код для пользователя."""
    return f"ref{user_id}"


def generate_client_email(user_id: int) -> str:
    """Генерирует email для X-UI клиента."""
    return f"user_{user_id}@freakvpn.local"


def generate_key_name(server_name: str) -> str:
    """Генерирует имя для ключа."""
    return f"FreakVPN_{server_name[:3].upper()}"


def format_bytes(bytes_count: int) -> str:
    """Форматирует байты в читаемый вид."""
    if bytes_count is None or bytes_count == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    value = float(bytes_count)
    
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    
    return f"{value:.1f} {units[index]}"


def get_status_text(expires_at: Optional[datetime], status: str) -> str:
    """Возвращает текст статуса пользователя."""
    from utils.constants import STATUS_ACTIVE, STATUS_EXPIRED, STATUS_TRIAL, STATUS_BLOCKED
    
    if status == "blocked":
        return STATUS_BLOCKED
    elif status == "trial":
        return STATUS_TRIAL
    elif expires_at and expires_at > datetime.now():
        return STATUS_ACTIVE
    else:
        return STATUS_EXPIRED


def get_tariff_name(months: int) -> str:
    """Возвращает название тарифа по количеству месяцев."""
    names = {
        1: "1 месяц",
        3: "3 месяца",
        6: "6 месяцев",
        12: "12 месяцев"
    }
    return names.get(months, f"{months} месяцев")


def get_flag_emoji(country_code: str) -> str:
    """Возвращает флаг страны по коду."""
    flags = {
        "NL": "🇳🇱",
        "DE": "🇩🇪",
        "FI": "🇫🇮",
        "US": "🇺🇸",
        "SG": "🇸🇬",
        "RU": "🇷🇺"
    }
    return flags.get(country_code.upper(), "🌍")

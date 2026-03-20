"""
Вспомогательные функции для бота.
"""

from datetime import datetime
from typing import Optional


def format_balance(kopecks: int) -> str:
    """
    Форматирование баланса из копеек в рубли.
    
    Args:
        kopecks: Сумма в копейках
        
    Returns:
        Строка с суммой в рублях
    """
    rubles = kopecks / 100
    return f"{rubles:,.0f}".replace(",", " ")


def format_date(dt: datetime, format_str: str = "%d.%m.%Y") -> str:
    """
    Форматирование даты.
    
    Args:
        dt: Объект datetime
        format_str: Формат вывода
        
    Returns:
        Отформатированная строка даты
    """
    if dt is None:
        return "Не указано"
    return dt.strftime(format_str)


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматирование даты и времени.
    
    Args:
        dt: Объект datetime
        format_str: Формат вывода
        
    Returns:
        Отформатированная строка даты и времени
    """
    if dt is None:
        return "Не указано"
    return dt.strftime(format_str)


def mask_key(key: str) -> str:
    """
    Маскирование ключа для отображения.
    
    Args:
        key: Полный ключ VLESS
        
    Returns:
        Маскированный ключ
    """
    if not key or len(key) < 30:
        return key
    return f"{key[:20]}...{key[-10:]}"


def generate_referral_code(user_id: int) -> str:
    """
    Генерация реферального кода на основе ID пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Реферальный код
    """
    return f"ref{user_id}"


def parse_referral_code(code: str) -> Optional[int]:
    """
    Парсинг реферального кода для извлечения ID пригласившего.
    
    Args:
        code: Реферальный код
        
    Returns:
        ID пригласившего или None
    """
    if code and code.startswith("ref"):
        try:
            return int(code[3:])
        except ValueError:
            return None
    return None


def get_status_text(status: str, expires_at: Optional[datetime] = None) -> str:
    """
    Получение текстового представления статуса.
    
    Args:
        status: Статус пользователя
        expires_at: Дата истечения подписки
        
    Returns:
        Текст статуса
    """
    from utils.constants import STATUS_ACTIVE, STATUS_EXPIRED, STATUS_TRIAL, STATUS_BLOCKED
    
    status_map = {
        "active": STATUS_ACTIVE,
        "trial": STATUS_TRIAL,
        "blocked": STATUS_BLOCKED,
    }
    
    if expires_at and expires_at < datetime.utcnow():
        return STATUS_EXPIRED
    
    return status_map.get(status, STATUS_EXPIRED)


def format_traffic(bytes_used: int, bytes_total: Optional[int] = None) -> str:
    """
    Форматирование трафика.
    
    Args:
        bytes_used: Использовано байт
        bytes_total: Всего байт (для лимитных тарифов)
        
    Returns:
        Строка с информацией о трафике
    """
    def bytes_to_gb(b: int) -> float:
        return round(b / (1024 ** 3), 1)
    
    used_gb = bytes_to_gb(bytes_used)
    
    if bytes_total is None or bytes_total == 0:
        return f"{used_gb} GB / Безлимит"
    
    total_gb = bytes_to_gb(bytes_total)
    return f"{used_gb} GB / {total_gb} GB"

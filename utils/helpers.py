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


def format_date(dt, format_str: str = "%d.%m.%Y") -> str:
    """
    Форматирование даты.
    
    Args:
        dt: Объект datetime или строка ISO формата
        format_str: Формат вывода
        
    Returns:
        Отформатированная строка даты
    """
    if dt is None:
        return "Не указано"
    
    # Если это строка - парсим в datetime
    if isinstance(dt, str):
        try:
            # SQLite формат: "2024-01-15 10:30:00" или "2024-01-15T10:30:00"
            dt = dt.replace("T", " ")
            if "." in dt:
                dt = dt.split(".")[0]  # Убираем миллисекунды
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return dt  # Возвращаем как есть если не удалось распарсить
    
    return dt.strftime(format_str)


def format_datetime(dt, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматирование даты и времени.
    
    Args:
        dt: Объект datetime или строка ISO формата
        format_str: Формат вывода
        
    Returns:
        Отформатированная строка даты и времени
    """
    if dt is None:
        return "Не указано"
    
    # Если это строка - парсим в datetime
    if isinstance(dt, str):
        try:
            dt = dt.replace("T", " ")
            if "." in dt:
                dt = dt.split(".")[0]
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return dt
    
    return dt.strftime(format_str)


def mask_key(key: str) -> str:
    """
    Маскирование ключа для отображения.
    
    Args:
        key: Полный ключ VLESS
        
    Returns:
        Маскированный ключ
    """
    if not key:
        return "Нет ключа"
    if len(key) < 30:
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


def get_status_text(status: str, expires_at=None) -> str:
    """
    Получение текстового представления статуса.
    
    Args:
        status: Статус пользователя
        expires_at: Дата истечения подписки (datetime или строка)
        
    Returns:
        Текст статуса
    """
    from utils.constants import STATUS_ACTIVE, STATUS_EXPIRED, STATUS_TRIAL, STATUS_BLOCKED
    
    status_map = {
        "active": STATUS_ACTIVE,
        "trial": STATUS_TRIAL,
        "blocked": STATUS_BLOCKED,
    }
    
    # Проверяем истечение подписки
    if expires_at:
        # Если строка - парсим в datetime
        if isinstance(expires_at, str):
            try:
                expires_at = expires_at.replace("T", " ")
                if "." in expires_at:
                    expires_at = expires_at.split(".")[0]
                expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                pass
        
        # Сравниваем с текущим временем
        if isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
            return STATUS_EXPIRED
    
    return status_map.get(status, STATUS_EXPIRED)


def parse_datetime(dt):
    """
    Парсинг даты из строки или datetime объекта.
    
    Args:
        dt: Строка ISO формата или datetime объект
        
    Returns:
        datetime объект или None
    """
    if dt is None:
        return None
    
    if isinstance(dt, datetime):
        return dt
    
    if isinstance(dt, str):
        try:
            dt = dt.replace("T", " ")
            if "." in dt:
                dt = dt.split(".")[0]
            return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return None
    
    return None


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


def get_country_flag(country_code: str) -> str:
    """
    Получение эмодзи флага по коду страны.
    
    Args:
        country_code: Код страны (NL, DE, FI, US, SG)
        
    Returns:
        Эмодзи флага
    """
    flags = {
        "NL": "🇳🇱",
        "DE": "🇩🇪",
        "FI": "🇫🇮",
        "US": "🇺🇸",
        "SG": "🇸🇬",
        "RU": "🇷🇺",
        "UA": "🇺🇦",
        "KZ": "🇰🇿",
        "BY": "🇧🇾",
    }
    return flags.get(country_code, "🌍")


def get_days_left(expires_at) -> int:
    """
    Получение количества дней до истечения срока.
    
    Args:
        expires_at: Дата истечения (datetime, строка ISO или None)
        
    Returns:
        Количество дней (0 если уже истек)
    """
    if not expires_at:
        return 0
    
    # Парсим дату если строка
    if isinstance(expires_at, str):
        expires_at = parse_datetime(expires_at)
    
    if not expires_at:
        return 0
    
    if isinstance(expires_at, datetime):
        delta = expires_at - datetime.utcnow()
        # Используем total_seconds для точного подсчёта
        total_seconds = delta.total_seconds()
        return max(0, int(total_seconds / 86400))
    
    return 0


def get_user_balance_rub(balance_kopecks: int) -> str:
    """
    Форматирование баланса пользователя для отображения.
    
    Args:
        balance_kopecks: Баланс в копейках
        
    Returns:
        Строка с балансом в рублях
    """
    return format_balance(balance_kopecks)

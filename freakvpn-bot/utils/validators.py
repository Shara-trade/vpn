"""
Валидаторы для входных данных.
"""
import re
from typing import Optional


def is_valid_user_id(text: str) -> bool:
    """Проверяет, является ли текст валидным Telegram user ID."""
    return text.isdigit() and len(text) <= 12


def is_valid_username(text: str) -> bool:
    """Проверяет, является ли текст валидным Telegram username."""
    if text.startswith("@"):
        text = text[1:]
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$", text))


def is_valid_amount(text: str) -> bool:
    """Проверяет, является ли текст валидной суммой."""
    try:
        amount = float(text)
        return amount > 0 and amount <= 1000000
    except ValueError:
        return False


def is_valid_vless_key(key: str) -> bool:
    """Проверяет, является ли текст валидным VLESS ключом."""
    pattern = r"^vless://[a-f0-9\-]{36}@[\w\.\-]+:\d+"
    return bool(re.match(pattern, key, re.IGNORECASE))


def is_valid_domain(domain: str) -> bool:
    """Проверяет, является ли текст валидным доменом."""
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$"
    return bool(re.match(pattern, domain))


def is_valid_ip(ip: str) -> bool:
    """Проверяет, является ли текст валидным IP-адресом."""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    
    parts = ip.split(".")
    return all(0 <= int(part) <= 255 for part in parts)


def is_valid_port(port: str) -> bool:
    """Проверяет, является ли текст валидным портом."""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except ValueError:
        return False


def extract_user_id_or_username(text: str) -> tuple[Optional[int], Optional[str]]:
    """
    Извлекает из текста user_id или username.
    Возвращает кортеж (user_id, username), один из которых None.
    """
    text = text.strip()
    
    if is_valid_user_id(text):
        return int(text), None
    
    if text.startswith("@"):
        text = text[1:]
    
    if is_valid_username("@" + text):
        return None, text
    
    return None, None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Очищает и ограничивает длину входного текста."""
    text = text.strip()
    text = re.sub(r"<[^>]+>", "", text)  # Удаляем HTML теги
    return text[:max_length]

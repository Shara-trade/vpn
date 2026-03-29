"""
Валидаторы для проверки ввода пользователя.
"""

import re
from typing import Optional, Tuple


def validate_user_id(user_id_str: str) -> Tuple[bool, Optional[int]]:
    """
    Валидация ID пользователя.
    
    Args:
        user_id_str: Строка с ID пользователя
        
    Returns:
        Кортеж (валидно ли, ID или None)
    """
    try:
        user_id = int(user_id_str)
        if user_id > 0:
            return True, user_id
    except ValueError:
        pass
    return False, None


def validate_amount(amount_str: str) -> Tuple[bool, Optional[int]]:
    """
    Валидация суммы (в рублях).
    
    Args:
        amount_str: Строка с суммой
        
    Returns:
        Кортеж (валидно ли, сумма в копейках или None)
    """
    try:
        # Удаляем пробелы и заменяем запятую на точку
        clean = amount_str.replace(" ", "").replace(",", ".")
        amount = float(clean)
        if amount > 0:
            return True, int(amount * 100)  # Конвертируем в копейки
    except ValueError:
        pass
    return False, None


def validate_vless_key(key: str) -> bool:
    """
    Валидация VLESS ключа.
    
    Args:
        key: Строка с ключом
        
    Returns:
        Валиден ли ключ
    """
    if not key:
        return False
    
    # Проверяем формат VLESS ключа
    pattern = r"^vless://[a-f0-9\-]{36}@[\w\.\-]+:\d+"
    return bool(re.match(pattern, key))


def validate_server_data(data: str) -> Tuple[bool, Optional[dict]]:
    """
    Валидация данных сервера при добавлении.
    
    Ожидаемый формат: Название;Страна;Домен;IP;X-UI порт;Логин;Пароль
    
    Args:
        data: Строка с данными сервера
        
    Returns:
        Кортеж (валидно ли, словарь с данными или None)
    """
    parts = data.split(";")
    
    if len(parts) != 7:
        return False, None
    
    name, country, domain, ip, port, login, password = [p.strip() for p in parts]
    
    # Проверяем порт
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            return False, None
    except ValueError:
        return False, None
    
    # Проверяем IP адрес
    ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    if not re.match(ip_pattern, ip):
        return False, None
    
    # Проверяем домен
    if not domain or len(domain) < 3:
        return False, None
    
    return True, {
        "name": name,
        "country_code": country.upper(),
        "domain": domain,
        "ip": ip,
        "port": port,
        "login": login,
        "password": password,
    }


def validate_username(username: str) -> bool:
    """
    Валидация Telegram username.
    
    Args:
        username: Username пользователя
        
    Returns:
        Валиден ли username
    """
    if not username:
        return False
    
    # Telegram username: 5-32 символа, буквы, цифры, подчеркивание
    pattern = r"^@?[a-zA-Z][a-zA-Z0-9_]{4,31}$"
    return bool(re.match(pattern, username.lstrip("@")))

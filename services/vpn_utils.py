"""
Утилиты для работы с VPN ключами.
Парсинг, генерация, валидация VLESS/VMess ключей.
"""

import re
import uuid as uuid_lib
from typing import Optional, Dict, Tuple
from urllib.parse import parse_qs, urlparse, unquote
from loguru import logger


class VlessKeyParser:
    """
    Парсер VLESS ключей.
    
    Пример ключа:
    vless://uuid@domain:port?security=tls&type=tcp#name
    """
    
    PATTERN = re.compile(
        r"^vless://(?P<uuid>[0-9a-fA-F-]+)@"
        r"(?P<host>[^:]+):(?P<port>\d+)"
        r"\?(?P<params>[^#]*)"
        r"#(?P<name>.*)$"
    )
    
    @classmethod
    def parse(cls, key: str) -> Optional[Dict]:
        """
        Парсинг VLESS ключа.
        
        Args:
            key: VLESS ключ в формате URI
            
        Returns:
            Словарь с компонентами ключа или None
        """
        try:
            # Удаляем пробелы
            key = key.strip()
            
            match = cls.PATTERN.match(key)
            
            if not match:
                logger.warning(f"VLESS key format mismatch: {key[:50]}...")
                return None
            
            result = match.groupdict()
            
            # Парсим параметры
            params = parse_qs(result["params"])
            
            return {
                "uuid": result["uuid"],
                "host": result["host"],
                "port": int(result["port"]),
                "name": unquote(result["name"]),
                "security": params.get("security", ["tls"])[0],
                "type": params.get("type", ["tcp"])[0],
                "flow": params.get("flow", [None])[0],
                "header_type": params.get("headerType", ["none"])[0],
            }
            
        except Exception as e:
            logger.error(f"VLESS key parse error: {e}")
            return None
    
    @classmethod
    def generate(
        cls,
        uuid: str,
        host: str,
        port: int = 443,
        name: str = "VPN",
        security: str = "tls",
        transport_type: str = "tcp",
        flow: str = None
    ) -> str:
        """
        Генерация VLESS ключа.
        
        Args:
            uuid: UUID клиента
            host: Домен или IP сервера
            port: Порт подключения
            name: Название ключа
            security: Тип безопасности (tls, reality)
            transport_type: Тип транспорта (tcp, ws, grpc)
            flow: Flow параметр
            
        Returns:
            VLESS ключ в формате URI
        """
        params = f"security={security}&type={transport_type}"
        
        if flow:
            params += f"&flow={flow}"
        
        key = f"vless://{uuid}@{host}:{port}?{params}#{name}"
        
        return key
    
    @classmethod
    def is_valid(cls, key: str) -> bool:
        """
        Проверка валидности VLESS ключа.
        
        Args:
            key: VLESS ключ
            
        Returns:
            True если ключ валиден
        """
        parsed = cls.parse(key)
        return parsed is not None
    
    @classmethod
    def extract_uuid(cls, key: str) -> Optional[str]:
        """
        Извлечение UUID из ключа.
        
        Args:
            key: VLESS ключ
            
        Returns:
            UUID или None
        """
        parsed = cls.parse(key)
        return parsed["uuid"] if parsed else None


class VmessKeyParser:
    """
    Парсер VMess ключей (Base64 encoded JSON).
    
    Пример ключа:
    vmess://eyJ2IjoiMiIsInBzIjoi...
    """
    
    @classmethod
    def parse(cls, key: str) -> Optional[Dict]:
        """
        Парсинг VMess ключа.
        
        Args:
            key: VMess ключ
            
        Returns:
            Словарь с компонентами или None
        """
        import base64
        
        try:
            key = key.strip()
            
            if not key.startswith("vmess://"):
                return None
            
            # Декодируем Base64
            encoded = key.replace("vmess://", "")
            decoded = base64.b64decode(encoded).decode("utf-8")
            
            import json
            data = json.loads(decoded)
            
            return {
                "uuid": data.get("id"),
                "host": data.get("add"),
                "port": int(data.get("port", 443)),
                "name": data.get("ps", "VPN"),
                "security": data.get("tls", ""),
                "type": data.get("net", "tcp"),
            }
            
        except Exception as e:
            logger.error(f"VMess key parse error: {e}")
            return None


class KeyValidator:
    """
    Валидатор VPN ключей.
    """
    
    @staticmethod
    def validate(key: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация ключа (VLESS или VMess).
        
        Args:
            key: VPN ключ
            
        Returns:
            Кортеж (is_valid, key_type)
        """
        key = key.strip()
        
        if key.startswith("vless://"):
            if VlessKeyParser.is_valid(key):
                return True, "vless"
        
        elif key.startswith("vmess://"):
            if VmessKeyParser.parse(key):
                return True, "vmess"
        
        return False, None
    
    @staticmethod
    def is_freakvpn_key(key: str) -> bool:
        """
        Проверка, что ключ принадлежит FreakVPN.
        
        Args:
            key: VPN ключ
            
        Returns:
            True если ключ FreakVPN
        """
        parsed = VlessKeyParser.parse(key)
        
        if not parsed:
            return False
        
        name = parsed.get("name", "").lower()
        return "freakvpn" in name


class KeyGenerator:
    """
    Генератор VPN ключей.
    """
    
    @staticmethod
    def generate_uuid() -> str:
        """
        Генерация нового UUID.
        
        Returns:
            UUID строка
        """
        return str(uuid_lib.uuid4())
    
    @staticmethod
    def generate_vless_key(
        host: str,
        port: int = 443,
        uuid: str = None,
        name: str = "FreakVPN",
        security: str = "tls",
        transport_type: str = "tcp",
        flow: str = None
    ) -> Dict[str, str]:
        """
        Генерация VLESS ключа.
        
        Args:
            host: Домен сервера
            port: Порт
            uuid: UUID (если None, генерируется новый)
            name: Название ключа
            security: Тип безопасности
            transport_type: Тип транспорта
            flow: Flow параметр
            
        Returns:
            Словарь с uuid и key
        """
        client_uuid = uuid or KeyGenerator.generate_uuid()
        
        key = VlessKeyParser.generate(
            uuid=client_uuid,
            host=host,
            port=port,
            name=name,
            security=security,
            transport_type=transport_type,
            flow=flow
        )
        
        return {
            "uuid": client_uuid,
            "key": key
        }


# ================== УТИЛИТЫ ДЛЯ ТРАФИКА ==================

def format_traffic(bytes_count: int) -> str:
    """
    Форматирование трафика в читаемый вид.
    
    Args:
        bytes_count: Количество байт
        
    Returns:
        Строка с форматированным значением (например, "15.2 GB")
    """
    if bytes_count == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    
    value = float(bytes_count)
    
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    
    if index < 2:
        return f"{int(value)} {units[index]}"
    else:
        return f"{value:.1f} {units[index]}"


def parse_traffic_limit(limit_str: str) -> int:
    """
    Парсинг строки лимита трафика в байты.
    
    Args:
        limit_str: Строка (например, "10GB", "100 MB")
        
    Returns:
        Количество байт
    """
    limit_str = limit_str.upper().strip()
    
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }
    
    for suffix, multiplier in multipliers.items():
        if limit_str.endswith(suffix):
            try:
                value = float(limit_str[:-len(suffix)])
                return int(value * multiplier)
            except ValueError:
                return 0
    
    return 0


# ================== ЭКСПОРТ ==================

__all__ = [
    "VlessKeyParser",
    "VmessKeyParser",
    "KeyValidator",
    "KeyGenerator",
    "format_traffic",
    "parse_traffic_limit",
]

"""
Сервис для работы с X-UI API.
"""
import aiohttp
from typing import Optional, Dict, Any
from loguru import logger

from database.models import Server


class XUIAPI:
    """Клиент для работы с X-UI API."""
    
    def __init__(self, server: Server):
        self.server = server
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookie: Optional[str] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Возвращает или создаёт сессию."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def login(self) -> bool:
        """Авторизация в X-UI панели."""
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{self.server.api_url}/login",
                json={
                    "username": self.server.api_username,
                    "password": self.server.api_password
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        # Сохраняем куки для следующих запросов
                        self.cookie = response.cookies.get("session")
                        logger.info(f"Успешная авторизация в X-UI: {self.server.name}")
                        return True
                
                logger.error(f"Ошибка авторизации в X-UI {self.server.name}: {response.status}")
                return False
        
        except Exception as e:
            logger.error(f"Ошибка подключения к X-UI {self.server.name}: {e}")
            return False
    
    async def create_client(
        self,
        email: str,
        uuid: str,
        total_gb: int = 0,
        expiry_days: int = 30,
        enable: bool = True,
        limit_ip: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Создаёт нового клиента в X-UI.
        
        Args:
            email: Уникальный email клиента
            uuid: UUID для ключа
            total_gb: Лимит трафика в GB (0 = безлимит)
            expiry_days: Дней до истечения
            enable: Активен ли клиент
            limit_ip: Лимит подключений с разных IP
        
        Returns:
            Данные созданного клиента или None при ошибке
        """
        session = await self._get_session()
        
        # Авторизуемся, если нужно
        if not self.cookie:
            if not await self.login():
                return None
        
        # Вычисляем время истечения
        import time
        expiry_time = int((time.time() + expiry_days * 86400) * 1000)
        
        payload = {
            "id": self.server.inbound_id,
            "settings": {
                "email": email,
                "id": uuid,
                "enable": enable,
                "flow": "xtls-rprx-vision",
                "limitIp": limit_ip,
                "totalGB": total_gb * 1024 * 1024 * 1024,  # Конвертируем GB в байты
                "expiryTime": expiry_time,
                "tgId": "",
                "subId": ""
            }
        }
        
        try:
            cookies = {"session": self.cookie.value} if self.cookie else {}
            
            async with session.post(
                f"{self.server.api_url}/inbound/addClient/",
                json=payload,
                cookies=cookies
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        logger.info(f"Клиент {email} создан на сервере {self.server.name}")
                        return data.get("obj")
                
                logger.error(f"Ошибка создания клиента {email}: {response.status}")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при создании клиента {email}: {e}")
            return None
    
    async def delete_client(self, email: str) -> bool:
        """
        Удаляет клиента из X-UI.
        
        Args:
            email: Email клиента для удаления
        
        Returns:
            True если успешно удалён
        """
        session = await self._get_session()
        
        if not self.cookie:
            if not await self.login():
                return False
        
        try:
            cookies = {"session": self.cookie.value} if self.cookie else {}
            
            async with session.post(
                f"{self.server.api_url}/inbound/delClient/{email}",
                cookies=cookies
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        logger.info(f"Клиент {email} удалён с сервера {self.server.name}")
                        return True
                
                return False
        
        except Exception as e:
            logger.error(f"Ошибка при удалении клиента {email}: {e}")
            return False
    
    async def get_client_traffic(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает статистику трафика клиента.
        
        Args:
            email: Email клиента
        
        Returns:
            Данные о трафике или None
        """
        session = await self._get_session()
        
        if not self.cookie:
            if not await self.login():
                return None
        
        try:
            cookies = {"session": self.cookie.value} if self.cookie else {}
            
            async with session.get(
                f"{self.server.api_url}/inbound/getClientTraffics/{email}",
                cookies=cookies
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data.get("obj")
                
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении трафика {email}: {e}")
            return None
    
    async def update_client(
        self,
        email: str,
        enable: Optional[bool] = None,
        total_gb: Optional[int] = None,
        expiry_days: Optional[int] = None,
        limit_ip: Optional[int] = None
    ) -> bool:
        """
        Обновляет настройки клиента.
        
        Args:
            email: Email клиента
            enable: Активен ли
            total_gb: Новый лимит трафика
            expiry_days: Новое время истечения
            limit_ip: Новый лимит IP
        
        Returns:
            True если успешно обновлён
        """
        session = await self._get_session()
        
        if not self.cookie:
            if not await self.login():
                return False
        
        # Получаем текущие настройки клиента
        # Здесь нужна логика получения текущих настроек и обновления
        
        return False  # Заглушка
    
    async def close(self):
        """Закрывает сессию."""
        if self.session and not self.session.closed:
            await self.session.close()


def generate_vless_key(
    uuid: str,
    server: Server,
    key_name: str = "FreakVPN"
) -> str:
    """
    Генерирует VLESS ключ.
    
    Args:
        uuid: UUID клиента
        server: Объект сервера
        key_name: Имя для ключа
    
    Returns:
        VLESS ключ в формате строки
    """
    return f"vless://{uuid}@{server.domain}:{server.port}?security=tls&type=tcp&headerType=none#{key_name}"


async def create_vpn_key(
    user_id: int,
    server: Server,
    expiry_days: int = 30
) -> Optional[str]:
    """
    Создаёт VPN ключ для пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        server: Объект сервера
        expiry_days: Дней до истечения
    
    Returns:
        VLESS ключ или None при ошибке
    """
    import uuid as uuid_lib
    
    # Генерируем данные для клиента
    client_email = f"user_{user_id}@freakvpn.local"
    client_uuid = str(uuid_lib.uuid4())
    
    # Создаём клиент в X-UI
    api = XUIAPI(server)
    
    try:
        result = await api.create_client(
            email=client_email,
            uuid=client_uuid,
            expiry_days=expiry_days
        )
        
        if result:
            # Генерируем ключ
            key_name = f"FreakVPN_{server.country_code}"
            key = generate_vless_key(client_uuid, server, key_name)
            
            return key
        
        return None
    
    finally:
        await api.close()


async def delete_vpn_key(server: Server, user_id: int) -> bool:
    """
    Удаляет VPN ключ пользователя.
    
    Args:
        server: Объект сервера
        user_id: Telegram ID пользователя
    
    Returns:
        True если успешно удалён
    """
    client_email = f"user_{user_id}@freakvpn.local"
    
    api = XUIAPI(server)
    
    try:
        return await api.delete_client(client_email)
    finally:
        await api.close()

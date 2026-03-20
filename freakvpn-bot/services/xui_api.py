"""
Сервис для работы с X-UI API (3X-UI панель).
Генерация и управление VLESS ключами.

Поддерживаемые версии: 3X-UI v1.x - v2.x
"""

import aiohttp
import uuid as uuid_lib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger


class XuiError(Exception):
    """Базовое исключение для X-UI ошибок."""
    pass


class XuiAuthError(XuiError):
    """Ошибка авторизации в X-UI."""
    pass


class XuiClientError(XuiError):
    """Ошибка при работе с клиентом."""
    pass


class XuiService:
    """
    Класс для работы с 3X-UI панелью.
    
    Поддерживает:
    - Авторизацию по username/password
    - Создание/удаление/обновление клиентов
    - Получение статистики трафика
    - Генерацию VLESS ключей
    """
    
    def __init__(self, server: Dict):
        """
        Инициализация сервиса.
        
        Args:
            server: Словарь с данными сервера из БД
                - id: ID сервера
                - name: Название сервера
                - domain: Домен сервера
                - api_url: URL API (например, http://1.2.3.4:54321)
                - api_username: Логин X-UI
                - api_password: Пароль X-UI
                - port: Порт подключения (default: 443)
                - inbound_id: ID inbound в X-UI (default: 1)
        """
        self.server = server
        self.base_url = server["api_url"].rstrip("/")
        self.username = server["api_username"]
        self.password = server["api_password"]
        self.inbound_id = server.get("inbound_id", 1)
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_cookie: Optional[str] = None
        self._is_authenticated = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Получение или создание сессии.
        
        Returns:
            aiohttp ClientSession
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def login(self) -> bool:
        """
        Авторизация в X-UI панели.
        
        Returns:
            True если авторизация успешна
            
        Raises:
            XuiAuthError: При ошибке авторизации
        """
        session = await self._get_session()
        
        try:
            url = f"{self.base_url}/login"
            data = {
                "username": self.username,
                "password": self.password
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get("success"):
                        # Сохраняем session cookie
                        self.session_cookie = response.cookies.get("session", None)
                        self._is_authenticated = True
                        logger.debug(f"X-UI login success: {self.server['name']}")
                        return True
                    else:
                        error_msg = result.get("msg", "Unknown error")
                        logger.error(f"X-UI login failed: {error_msg}")
                        raise XuiAuthError(f"Login failed: {error_msg}")
                else:
                    logger.error(f"X-UI login HTTP error: {response.status}")
                    raise XuiAuthError(f"HTTP error: {response.status}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"X-UI connection error: {e}")
            raise XuiAuthError(f"Connection error: {e}")
    
    async def ensure_authenticated(self) -> bool:
        """
        Проверка и обеспечение авторизации.
        
        Returns:
            True если авторизован
        """
        if self._is_authenticated and self.session_cookie:
            return True
        
        return await self.login()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        retry: bool = True
    ) -> Optional[Dict]:
        """
        Выполнение запроса к X-UI API.
        
        Args:
            method: HTTP метод (GET, POST)
            endpoint: Endpoint API
            data: Данные для отправки
            retry: Повторить при ошибке авторизации
            
        Returns:
            Ответ API или None
        """
        if not await self.ensure_authenticated():
            return None
        
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        cookies = {"session": self.session_cookie} if self.session_cookie else {}
        
        try:
            if method.upper() == "GET":
                async with session.get(url, cookies=cookies) as response:
                    return await self._handle_response(response, endpoint, retry)
            elif method.upper() == "POST":
                async with session.post(url, json=data, cookies=cookies) as response:
                    return await self._handle_response(response, endpoint, retry)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
        except aiohttp.ClientError as e:
            logger.error(f"X-UI request error ({endpoint}): {e}")
            return None
    
    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        endpoint: str,
        retry: bool
    ) -> Optional[Dict]:
        """
        Обработка ответа от API.
        
        Args:
            response: HTTP ответ
            endpoint: Endpoint для логирования
            retry: Нужно ли повторить при 401
            
        Returns:
            Данные ответа или None
        """
        if response.status == 200:
            result = await response.json()
            
            if result.get("success"):
                return result
            else:
                logger.error(f"X-UI API error ({endpoint}): {result.get('msg', 'Unknown')}")
                return None
                
        elif response.status == 401 and retry:
            # Сессия истекла, пробуем авторизоваться заново
            logger.warning(f"X-UI session expired, re-authenticating...")
            self._is_authenticated = False
            self.session_cookie = None
            
            if await self.login():
                # Повторяем запрос без retry
                return await self._make_request(
                    response.method,
                    endpoint,
                    retry=False
                )
            return None
    
        else:
            logger.error(f"X-UI HTTP error ({endpoint}): {response.status}")
            return None
    
    async def get_inbound(self) -> Optional[Dict]:
        """
        Получение информации о inbound.
        
        Returns:
            Данные inbound или None
        """
        result = await self._make_request(
            "GET",
            f"/panel/api/inbounds/get/{self.inbound_id}"
        )
        
        if result:
            return result.get("obj")
        return None
    
    async def create_client(
        self, 
        user_id: int, 
        days: int = 30,
        traffic_limit_gb: int = 0,
        email: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создание клиента в X-UI.
        
        Args:
            user_id: Telegram ID пользователя
            days: Количество дней подписки
            traffic_limit_gb: Лимит трафика в GB (0 = безлимит)
            email: Email клиента (если None, генерируется автоматически)
            
        Returns:
            Словарь с данными ключа или None:
                - uuid: UUID клиента
                - key: VLESS ключ
                - email: Email клиента
                - expires_at: Дата истечения
                - traffic_limit: Лимит трафика
        """
        if not await self.ensure_authenticated():
            logger.error("Не удалось авторизоваться в X-UI")
            return None
        
        # Генерируем UUID
        client_uuid = str(uuid_lib.uuid4())
        
        # Email для идентификации клиента
        client_email = email or f"user_{user_id}"
        
        # Вычисляем время истечения (в миллисекундах)
        expires_at = datetime.utcnow() + timedelta(days=days)
        expiry_time = int(expires_at.timestamp() * 1000)
        
        # Лимит трафика в байтах (0 = безлимит)
        total_bytes = traffic_limit_gb * 1024 * 1024 * 1024 if traffic_limit_gb > 0 else 0
        
        # Данные клиента для VLESS
        client_settings = {
            "id": client_uuid,
            "email": client_email,
            "enable": True,
            "flow": "xtls-rprx-vision",
            "limitIp": 0,
            "totalGB": total_bytes,
            "expiryTime": expiry_time,
            "tgId": str(user_id),
            "subId": ""
        }
        
        try:
            # Формируем payload для добавления клиента
            payload = {
                "id": client_uuid,
                "settings": json.dumps({"clients": [client_settings]})
            }
            
            result = await self._make_request(
                "POST",
                f"/panel/api/inbounds/addClient/{self.inbound_id}",
                data=payload
            )
            
            if result:
                # Формируем VLESS ключ
                key = self._generate_vless_key(client_uuid)
                
                logger.info(
                    f"X-UI клиент создан: user_id={user_id}, uuid={client_uuid}, server={self.server['name']}"
                )
                
                return {
                    "uuid": client_uuid,
                    "key": key,
                    "email": client_email,
                    "expires_at": expires_at,
                    "traffic_limit": traffic_limit_gb
                }
            else:
                logger.error(f"X-UI create client failed for user_id={user_id}")
                return None
                    
        except Exception as e:
            logger.error(f"X-UI create client error: {e}")
            return None
    
    async def delete_client(self, client_uuid: str) -> bool:
        """
        Удаление клиента из X-UI.
        
        Args:
            client_uuid: UUID клиента
            
        Returns:
            True если удаление успешно
        """
        result = await self._make_request(
            "POST",
            f"/panel/api/inbounds/delClient/{self.inbound_id}/{client_uuid}"
        )
        
        if result:
            logger.info(f"X-UI клиент удален: uuid={client_uuid}")
            return True
        
        return False
    
    async def update_client(
        self, 
        client_uuid: str, 
        days: int = None,
        enable: bool = None,
        traffic_limit_gb: int = None
    ) -> bool:
        """
        Обновление клиента в X-UI.
        
        Args:
            client_uuid: UUID клиента
            days: Новое количество дней (от текущего момента)
            enable: Включить/выключить клиента
            traffic_limit_gb: Новый лимит трафика
            
        Returns:
            True если обновление успешно
        """
        # Получаем текущие данные inbound
        inbound = await self.get_inbound()
        
        if not inbound:
            logger.error("Не удалось получить inbound для обновления клиента")
            return False
        
        # Парсим настройки клиентов
        try:
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
        except json.JSONDecodeError:
            logger.error("Ошибка парсинга настроек inbound")
            return False
        
        # Ищем клиента по UUID
        client_found = False
        for client in clients:
            if client.get("id") == client_uuid:
                client_found = True
                
                # Обновляем данные
                if days is not None:
                    new_expiry = datetime.utcnow() + timedelta(days=days)
                    client["expiryTime"] = int(new_expiry.timestamp() * 1000)
                
                if enable is not None:
                    client["enable"] = enable
                
                if traffic_limit_gb is not None:
                    client["totalGB"] = traffic_limit_gb * 1024 * 1024 * 1024
                
                break
        
        if not client_found:
            logger.error(f"Клиент не найден: uuid={client_uuid}")
            return False
        
        # Обновляем inbound
        payload = {
            "id": self.inbound_id,
            "settings": json.dumps(settings)
        }
        
        result = await self._make_request(
            "POST",
            f"/panel/api/inbounds/update/{self.inbound_id}",
            data=payload
        )
        
        if result:
            logger.info(f"X-UI клиент обновлен: uuid={client_uuid}")
            return True
        
        return False
    
    async def get_client_traffic(self, client_identifier: str) -> Optional[Dict]:
        """
        Получение статистики трафика клиента (по email или UUID).
        
        Args:
            client_identifier: Email или UUID клиента
            
        Returns:
            Словарь со статистикой или None:
                - up: Исходящий трафик (байты)
                - down: Входящий трафик (байты)
                - total: Общий трафик (байты)
        """
        # Если это UUID (содержит дефисы и длина 36), сначала найдем email
        if "-" in client_identifier and len(client_identifier) == 36:
            return await self.get_client_traffic_by_uuid(client_identifier)
        
        # Иначе считаем, что это email
        result = await self._make_request(
            "GET",
            f"/panel/api/inbounds/getClientTraffics/{client_identifier}"
        )
        
        if result:
            traffic = result.get("obj", {})
            return {
                "up": traffic.get("up", 0),
                "down": traffic.get("down", 0),
                "total": traffic.get("down", 0) + traffic.get("up", 0)
            }
        
        return None
    
    async def get_client_traffic_by_uuid(self, client_uuid: str) -> Optional[Dict]:
        """
        Получение статистики трафика клиента по UUID.
        
        Args:
            client_uuid: UUID клиента
            
        Returns:
            Словарь со статистикой или None
        """
        # Получаем всех клиентов на inbound
        clients = await self.get_all_clients()
        
        if not clients:
            return None
        
        # Ищем клиента по UUID
        for client in clients:
            if client.get("id") == client_uuid:
                email = client.get("email")
                if email:
                    return await self.get_client_traffic(email)
        
        return None
    
    async def reset_client_traffic(self, email: str) -> bool:
        """
        Сброс статистики трафика клиента.
        
        Args:
            email: Email клиента
            
        Returns:
            True если сброс успешен
        """
        result = await self._make_request(
            "POST",
            f"/panel/api/inbounds/resetClientTraffic/{email}"
        )
        
        return result is not None
    
    async def get_all_clients(self) -> Optional[List[Dict]]:
        """
        Получение списка всех клиентов на сервере.
        
        Returns:
            Список клиентов или None
        """
        inbound = await self.get_inbound()
        
        if not inbound:
            return None
        
        try:
            settings = json.loads(inbound.get("settings", "{}"))
            return settings.get("clients", [])
        except json.JSONDecodeError:
            logger.error("Ошибка парсинга настроек inbound")
            return None
    
    async def check_connection(self) -> bool:
        """
        Проверка подключения к серверу X-UI.
        
        Returns:
            True если сервер доступен
        """
        try:
            return await self.login()
        except XuiAuthError:
            return False
        except Exception as e:
            logger.error(f"X-UI connection check error: {e}")
            return False
    
    def _generate_vless_key(
        self,
        client_uuid: str,
        security: str = "tls",
        transport_type: str = "tcp"
    ) -> str:
        """
        Генерация VLESS ключа.
        
        Args:
            client_uuid: UUID клиента
            security: Тип безопасности (tls, reality)
            transport_type: Тип транспорта (tcp, ws, grpc)
            
        Returns:
            VLESS ключ в формате URI
        """
        domain = self.server["domain"]
        port = self.server.get("port", 443)
        server_name = self.server.get("name", "VPN")[:3].upper()
        
        # Формируем имя для ключа
        key_name = f"FreakVPN_{server_name}"
        
        # Базовый формат VLESS ключа
        key = (
            f"vless://{client_uuid}@{domain}:{port}"
            f"?security={security}&type={transport_type}"
        )
        
        # Добавляем параметры в зависимости от типа безопасности
        if security == "reality":
            # Для Reality добавляем дополнительные параметры
            # (можно расширить при необходимости)
            key += "&flow=xtls-rprx-vision"
        
        # Добавляем имя ключа
        key += f"#{key_name}"
        
        return key
    
    async def close(self):
        """Закрытие сессии."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self._is_authenticated = False
            self.session_cookie = None


class XuiServiceFactory:
    """
    Фабрика для создания и управления X-UI сервисами.
    
    Использует паттерн Singleton для каждого сервера.
    """
    
    _instances: Dict[int, XuiService] = {}
    
    @classmethod
    async def get_service(cls, server: Dict) -> XuiService:
        """
        Получение или создание X-UI сервиса для сервера.
        
        Args:
            server: Данные сервера из БД
            
        Returns:
            Экземпляр XuiService
        """
        server_id = server["id"]
        
        if server_id not in cls._instances:
            cls._instances[server_id] = XuiService(server)
        
        return cls._instances[server_id]
    
    @classmethod
    async def get_service_by_id(cls, server_id: int) -> Optional[XuiService]:
        """
        Получение сервиса по ID сервера.
        
        Args:
            server_id: ID сервера
            
        Returns:
            Экземпляр XuiService или None
        """
        return cls._instances.get(server_id)
    
    @classmethod
    async def close_all(cls):
        """Закрытие всех сессий."""
        for service in cls._instances.values():
            await service.close()
        cls._instances.clear()

    @classmethod
    async def remove_service(cls, server_id: int):
        """
        Удаление сервиса из кэша.
        
        Args:
            server_id: ID сервера
        """
        if server_id in cls._instances:
            await cls._instances[server_id].close()
            del cls._instances[server_id]


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def create_key_for_user(
    server: Dict,
    user_id: int,
    days: int = 30,
    traffic_limit_gb: int = 0
) -> Optional[Dict]:
    """
    Удобная функция для создания ключа для пользователя.
    
    Args:
        server: Данные сервера
        user_id: Telegram ID пользователя
        days: Количество дней
        traffic_limit_gb: Лимит трафика
        
    Returns:
        Данные ключа или None
    """
    service = await XuiServiceFactory.get_service(server)
    return await service.create_client(user_id, days, traffic_limit_gb)


async def delete_key_for_user(server: Dict, client_uuid: str) -> bool:
    """
    Удаление ключа пользователя.
    
    Args:
        server: Данные сервера
        client_uuid: UUID клиента
        
    Returns:
        True если успешно
    """
    service = await XuiServiceFactory.get_service(server)
    return await service.delete_client(client_uuid)


async def check_server_connection(server: Dict) -> bool:
    """
    Проверка подключения к серверу X-UI.
    
    Args:
        server: Данные сервера
        
    Returns:
        True если сервер доступен
    """
    service = XuiService(server)
    try:
        return await service.check_connection()
    finally:
        await service.close()

"""
Адаптер для 3x-ui панели версии 2.8.11
"""
import aiohttp
import uuid as uuid_lib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger


class XuiError(Exception):
    """Базовое исключение для XUI ошибок"""
    pass


class XuiAuthError(XuiError):
    """Ошибка авторизации в XUI"""
    pass


class XuiClientError(XuiError):
    """Ошибка работы с клиентом XUI"""
    pass


class XuiService:
    """Сервис для работы с 3x-ui панелью"""
    
    def __init__(self, server: Dict):
        """
        Инициализация сервиса
        
        Args:
            server: Словарь с данными сервера из БД
        """
        self.server = server
        # Базовый URL берём из БД, он уже содержит кастомный путь
        self.base_url = server["api_url"].rstrip('/')
        self.username = server["api_username"]
        self.password = server["api_password"]
        self.inbound_id = server.get("inbound_id", 1)
        self.session = None
        self.cookies = None
        
        logger.info(f"3x-ui сервер: {server.get('name')}")
        logger.info(f"Базовый URL: {self.base_url}")
        logger.info(f"Inbound ID: {self.inbound_id}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение HTTP сессии с отключенной проверкой SSL"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout, 
                connector=connector
            )
        return self.session

    async def login(self) -> bool:
        """
        Авторизация в панели 3x-ui
        
        Returns:
            True если авторизация успешна
        """
        session = await self._get_session()
        url = f"{self.base_url}/login"
        
        logger.info(f"Авторизация в 3x-ui: {url}")
        
        try:
            async with session.post(
                url,
                json={
                    "username": self.username,
                    "password": self.password
                },
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        self.cookies = resp.cookies
                        logger.info("✅ Авторизация успешна")
                        return True
                    else:
                        logger.error(f"❌ Ошибка авторизации: {result}")
                        return False
                else:
                    text = await resp.text()
                    logger.error(f"❌ HTTP {resp.status}: {text[:200]}")
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка при авторизации: {e}")
            return False

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """
        Выполнение авторизованного запроса к API
        
        Args:
            method: HTTP метод (GET, POST)
            endpoint: Путь эндпоинта (начинается с /panel/api/...)
            data: Данные для отправки (для POST)
            
        Returns:
            JSON ответ или None
        """
        # Проверяем авторизацию
        if not self.cookies:
            if not await self.login():
                return None
        
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.request(
                method,
                url,
                json=data,
                headers={"Content-Type": "application/json"},
                cookies=self.cookies
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result
                elif resp.status == 401:
                    # Сессия истекла, перелогиниваемся
                    logger.warning("Сессия истекла, перелогиниваемся...")
                    self.cookies = None
                    if await self.login():
                        return await self._request(method, endpoint, data)
                    return None
                else:
                    logger.error(f"❌ HTTP {resp.status} на {url}")
                    return None
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return None
    
    async def get_inbound(self) -> Optional[Dict]:
        """
        Получение информации об инбаунде
        
        Returns:
            Объект инбаунда или None
        """
        result = await self._request(
            "GET",
            f"/panel/api/inbounds/get/{self.inbound_id}"
        )
        if result and result.get("success"):
            return result.get("obj")
        return None
    
    async def create_client(self, user_id: int, days: int = 30, email: str = None) -> Optional[Dict]:
        """
        Создание нового клиента в панели
        
        Args:
            user_id: ID пользователя в боте
            days: Срок действия в днях
            email: Email клиента (опционально)
            
        Returns:
            Словарь с данными клиента или None
        """
        # Получаем текущий инбаунд
        inbound = await self.get_inbound()
        if not inbound:
            logger.error("Не удалось получить инбаунд")
            return None
        
        # Генерируем UUID и email
        client_uuid = str(uuid_lib.uuid4())
        timestamp = int(datetime.now().timestamp())
        client_email = email or f"user_{user_id}_{timestamp}"
        
        # Вычисляем время истечения в миллисекундах
        expiry_time = int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)
        
        # Парсим существующих клиентов из settings
        try:
            settings = json.loads(inbound.get("settings", "{}"))
        except:
            settings = {"clients": []}
        
        clients = settings.get("clients", [])
        
        # Создаём нового клиента
        new_client = {
            "id": client_uuid,
            "email": client_email,
            "enable": True,
            "expiryTime": expiry_time,
            "flow": "xtls-rprx-vision"
        }
        clients.append(new_client)
        settings["clients"] = clients
        
        # Обновляем инбаунд
        inbound["settings"] = json.dumps(settings)
        
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/update/{self.inbound_id}",
            data=inbound
        )
        
        if result and result.get("success"):
            # Генерируем VLESS ключ
            vless_key = self._generate_vless_key(client_uuid)
            
            logger.info(f"✅ Создан клиент: {client_email}, UUID: {client_uuid}")
            
            return {
                "uuid": client_uuid,
                "key": vless_key,
                "email": client_email,
                "expires_at": datetime.utcnow() + timedelta(days=days)
            }
        
        logger.error("❌ Не удалось создать клиента")
        return None
    
    async def delete_client(self, client_uuid: str) -> bool:
        """
        Удаление клиента из панели
        
        Args:
            client_uuid: UUID клиента
            
        Returns:
            True если успешно
        """
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/{self.inbound_id}/delClient/{client_uuid}"
        )
        
        if result and result.get("success"):
            logger.info(f"✅ Удалён клиент: {client_uuid}")
            return True
        
        logger.error(f"❌ Не удалось удалить клиента: {client_uuid}")
        return False

    async def update_client_expiry(self, client_uuid: str, days: int) -> bool:
        """
        Продление срока действия клиента
        
        Args:
            client_uuid: UUID клиента
            days: Количество дней для продления
            
        Returns:
            True если успешно
        """
        # Получаем текущий инбаунд
        inbound = await self.get_inbound()
        if not inbound:
            return False
        
        # Парсим клиентов
        try:
            settings = json.loads(inbound.get("settings", "{}"))
        except:
            settings = {"clients": []}
        
        clients = settings.get("clients", [])
        
        # Ищем и обновляем клиента
        found = False
        new_expiry = int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)
        
        for client in clients:
            if client.get("id") == client_uuid:
                client["expiryTime"] = new_expiry
                found = True
                break
        
        if not found:
            logger.error(f"Клиент не найден: {client_uuid}")
            return False
        
        # Обновляем инбаунд
        settings["clients"] = clients
        inbound["settings"] = json.dumps(settings)
        
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/update/{self.inbound_id}",
            data=inbound
        )
        
        if result and result.get("success"):
            logger.info(f"✅ Продлён клиент: {client_uuid} на {days} дней")
            return True
        
        logger.error(f"❌ Не удалось продлить клиента: {client_uuid}")
        return False
    
    async def get_client_traffic_by_uuid(self, client_uuid: str) -> Optional[Dict]:
        """
        Получение трафика клиента по UUID
        
        Args:
            client_uuid: UUID клиента
            
        Returns:
            Словарь с трафиком или None
        """
        result = await self._request(
            "GET",
            "/panel/api/inbounds/getClientTraffic"
        )
        
        if result and result.get("success"):
            clients = result.get("obj", [])
            for client in clients:
                if client.get("id") == client_uuid:
                    return client
        return None
    
    async def check_connection(self) -> bool:
        """
        Проверка соединения с панелью
        
        Returns:
            True если соединение работает
        """
        return await self.login()
    
    def _generate_vless_key(self, client_uuid: str) -> str:
        """
        Генерация VLESS ключа для клиента
        
        Args:
            client_uuid: UUID клиента
            
        Returns:
            Строка с VLESS ключом
        """
        domain = self.server.get("domain", self.server.get("ip", ""))
        port = self.server.get("port", 443)
        name = self.server.get("name", "VPN")
        
        key = f"vless://{client_uuid}@{domain}:{port}?security=tls&type=tcp&flow=xtls-rprx-vision#{name}"
        return key
    
    async def close(self):
        """Закрытие HTTP сессии"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self.cookies = None


async def check_server_connection(server: Dict) -> bool:
    """
    Проверка подключения к серверу 3x-ui
    
    Args:
        server: Словарь с данными сервера
        
    Returns:
        True если подключение работает
    """
    try:
        xui = XuiService(server)
        result = await xui.check_connection()
        await xui.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка проверки подключения: {e}")
        return False


import aiohttp
import uuid as uuid_lib
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger


_semaphores = {}


class XuiError(Exception):
    pass


class XuiAuthError(XuiError):
    pass


class XuiService:
    def __init__(self, server: Dict):
        self.server = server
        self.base_url = server["api_url"].rstrip("/")
        self.username = server["api_username"]
        self.password = server["api_password"]
        self.inbound_id = server.get("inbound_id", 1)
        self.session = None
        self._authenticated = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def _get_semaphore(self):
        server_id = self.server["id"]
        if server_id not in _semaphores:
            _semaphores[server_id] = asyncio.Semaphore(5)
        return _semaphores[server_id]

    async def login(self) -> bool:
        session = await self._get_session()
        url = f"{self.base_url}/login"
        data = {"username": self.username, "password": self.password}

        try:
            async with session.post(url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        self._authenticated = True
                        logger.debug(f"Успешный вход в X-UI: {self.server['name']}")
                        return True
                    else:
                        logger.error(f"Ошибка входа: {result.get('msg')}")
                        return False
                else:
                    logger.error(f"Ошибка HTTP {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        sem = await self._get_semaphore()
        
        async with sem:
            if not self._authenticated:
                if not await self.login():
                    return None

            session = await self._get_session()
            url = f"{self.base_url}{endpoint}"

            try:
                async with session.request(method, url, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("success"):
                            return result
                        else:
                            logger.error(f"Ошибка API: {result.get('msg')}")
                            return None
                    elif resp.status == 401:
                        self._authenticated = False
                        return await self._request(method, endpoint, data)
                    else:
                        logger.error(f"Ошибка HTTP {resp.status}: {endpoint}")
                        return None
            except Exception as e:
                logger.error(f"Ошибка запроса: {e}")
                return None

    async def get_inbound(self) -> Optional[Dict]:
        result = await self._request("GET", f"/xui/API/inbounds/get/{self.inbound_id}")
        if result:
            return result.get("obj")
        return None

    async def create_client(self, user_id: int, days: int = 30, email: str = None) -> Optional[Dict]:
        client_uuid = str(uuid_lib.uuid4())
        client_email = email or f"user_{user_id}"
        expiry_time = int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)

        client_data = {
            "id": client_uuid,
            "email": client_email,
            "enable": True,
            "expiryTime": expiry_time,
            "flow": "xtls-rprx-vision"
        }

        inbound = await self.get_inbound()
        if not inbound:
            return None

        try:
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
            clients.append(client_data)
            settings["clients"] = clients

            payload = {
                "id": self.inbound_id,
                "settings": json.dumps(settings)
            }

            result = await self._request("POST", "/xui/API/inbounds/update", data=payload)
            if result:
                key = self._generate_vless_key(client_uuid)
                return {
                    "uuid": client_uuid,
                    "key": key,
                    "email": client_email,
                    "expires_at": datetime.utcnow() + timedelta(days=days)
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка создания клиента: {e}")
            return None

    async def delete_client(self, client_uuid: str) -> bool:
        result = await self._request("POST", f"/xui/API/inbounds/delClient/{client_uuid}")
        return result is not None

    async def update_client_expiry(self, client_uuid: str, days: int) -> bool:
        inbound = await self.get_inbound()
        if not inbound:
            return False

        try:
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
            for client in clients:
                if client.get("id") == client_uuid:
                    new_expiry = int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)
                    client["expiryTime"] = new_expiry
                    break

            payload = {
                "id": self.inbound_id,
                "settings": json.dumps(settings)
            }
            result = await self._request("POST", "/xui/API/inbounds/update", data=payload)
            return result is not None
        except Exception as e:
            logger.error(f"Ошибка обновления клиента: {e}")
            return False

    async def check_connection(self) -> bool:
        return await self.login()

    def _generate_vless_key(self, client_uuid: str) -> str:
        domain = self.server["domain"]
        port = self.server.get("port", 443)
        key = f"vless://{client_uuid}@{domain}:{port}?security=tls&type=tcp#StarinaVPN"
        return key

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self._authenticated = False


async def check_server_connection(server: Dict) -> bool:
    """
    Проверка подключения к X-UI серверу.
    
    Args:
        server: Словарь с данными сервера (api_url, api_username, api_password)
        
    Returns:
        True если подключение успешно
    """
    try:
        xui = XuiService(server)
        result = await xui.check_connection()
        await xui.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка проверки подключения к серверу: {e}")
        return False
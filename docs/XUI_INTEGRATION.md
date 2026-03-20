# Интеграция с X-UI API

## Обзор

FreakVPN использует **3X-UI панель** для управления VPN-серверами и генерации VLESS ключей. Интеграция позволяет автоматически создавать, удалять и управлять клиентами через API.

## Архитектура

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Telegram Bot  │─────▶│   XuiService    │─────▶│  3X-UI Panel    │
│   (Aiogram)     │      │   (aiohttp)     │      │   (Xray)        │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                │
                                ▼
                         ┌─────────────────┐
                         │  SQLite / PG    │
                         │  (Servers DB)   │
                         └─────────────────┘
```

## Структура файлов

```
services/
├── xui_api.py      # Основной сервис для работы с X-UI API
├── vpn_utils.py    # Утилиты для парсинга/генерации ключей
└── __init__.py
```

## Основные компоненты

### 1. XuiService

Главный класс для работы с X-UI панелью:

```python
from services.xui_api import XuiService

# Данные сервера из БД
server = {
    "id": 1,
    "name": "Амстердам",
    "domain": "ams.freakvpn.ru",
    "api_url": "http://45.67.89.10:54321",
    "api_username": "admin",
    "api_password": "secret",
    "port": 443,
    "inbound_id": 1
}

service = XuiService(server)

# Проверка подключения
if await service.check_connection():
    print("✅ Подключено!")

# Создание клиента
result = await service.create_client(
    user_id=123456789,
    days=30,
    traffic_limit_gb=0  # 0 = безлимит
)

print(f"Ключ: {result['key']}")

# Удаление клиента
await service.delete_client(result['uuid'])

# Закрытие сессии
await service.close()
```

### 2. XuiServiceFactory

Фабрика для управления сервисами (Singleton):

```python
from services.xui_api import XuiServiceFactory

# Получение сервиса (создается один раз)
service = await XuiServiceFactory.get_service(server)

# Закрытие всех сессий
await XuiServiceFactory.close_all()
```

### 3. Вспомогательные функции

```python
from services.xui_api import create_key_for_user, delete_key_for_user

# Быстрое создание ключа
result = await create_key_for_user(
    server=server,
    user_id=123456789,
    days=30
)

# Быстрое удаление ключа
await delete_key_for_user(server, client_uuid)
```

## API методы

### Авторизация

```python
# Автоматическая авторизация при первом запросе
# Сессия сохраняется в cookies

if await service.login():
    print("Авторизован!")
```

### Создание клиента

```python
result = await service.create_client(
    user_id=123456789,      # Telegram ID пользователя
    days=30,                 # Количество дней
    traffic_limit_gb=0,      # Лимит трафика (0 = безлимит)
    email="custom@email.com" # Опционально
)

# Возвращает:
{
    "uuid": "8940e8e7-915d-4f78-9c4b-300eac0f7cdb",
    "key": "vless://uuid@domain:443?security=tls&type=tcp#FreakVPN",
    "email": "user_123456789",
    "expires_at": datetime(2026, 4, 20),
    "traffic_limit": 0
}
```

### Удаление клиента

```python
success = await service.delete_client(client_uuid)
```

### Обновление клиента

```python
success = await service.update_client(
    client_uuid=client_uuid,
    days=30,              # Продлить на 30 дней
    enable=True,          # Включить/выключить
    traffic_limit_gb=100  # Новый лимит трафика
)
```

### Получение трафика

```python
traffic = await service.get_client_traffic(email="user_123456789")

# Возвращает:
{
    "up": 1073741824,    # Исходящий (байты)
    "down": 5368709120,  # Входящий (байты)
    "total": 6442450944  # Общий
}
```

## Утилиты для ключей

### Парсинг VLESS ключа

```python
from services.vpn_utils import VlessKeyParser

parsed = VlessKeyParser.parse(key)

# Возвращает:
{
    "uuid": "...",
    "host": "ams.freakvpn.ru",
    "port": 443,
    "name": "FreakVPN_AMS",
    "security": "tls",
    "type": "tcp"
}
```

### Генерация ключа

```python
from services.vpn_utils import KeyGenerator

result = KeyGenerator.generate_vless_key(
    host="ams.freakvpn.ru",
    port=443,
    name="FreakVPN_AMS"
)

print(result["key"])
print(result["uuid"])
```

### Валидация ключа

```python
from services.vpn_utils import KeyValidator

is_valid, key_type = KeyValidator.validate(key)

if is_valid:
    print(f"Валидный {key_type} ключ")
```

### Форматирование трафика

```python
from services.vpn_utils import format_traffic

print(format_traffic(6442450944))  # "6.0 GB"
print(format_traffic(1073741824))  # "1.0 GB"
print(format_traffic(524288))      # "512 KB"
```

## Тестирование подключения

### Через скрипт

```bash
cd freakvpn-bot
python test_xui_connection.py
```

Или с параметрами:

```bash
python test_xui_connection.py \
    --url http://45.67.89.10:54321 \
    --user admin \
    --pass yourpassword \
    --inbound 1
```

### Программно

```python
from services.xui_api import check_server_connection

server = {
    "api_url": "http://45.67.89.10:54321",
    "api_username": "admin",
    "api_password": "secret"
}

if await check_server_connection(server):
    print("✅ Сервер доступен")
```

## Настройка X-UI панели

### Требования к серверу

1. **3X-UI панель** установлена и настроена
2. **Inbound** с протоколом VLESS создан
3. **TLS сертификат** установлен (Let's Encrypt или свой)
4. **API доступен** по адресу `http://IP:PORT`

### Создание inbound

1. Откройте X-UI панель
2. Перейдите в **Inbounds** → **Add Inbound**
3. Настройте:
   - **Remark**: `FreakVPN_AMS`
   - **Protocol**: `VLESS`
   - **Port**: `443`
   - **Security**: `tls`
   - **SNI**: `ams.freakvpn.ru`
4. Сохраните и запомните **Inbound ID**

### Добавление сервера в БД

```python
from database.queries import create_server

await create_server(
    name="Амстердам",
    country_code="NL",
    domain="ams.freakvpn.ru",
    ip="45.67.89.10",
    api_url="http://45.67.89.10:54321",
    api_username="admin",
    api_password="your_secure_password",
    port=443,
    inbound_id=1,
    is_trial=False
)
```

## Обработка ошибок

### Исключения

```python
from services.xui_api import XuiError, XuiAuthError, XuiClientError

try:
    result = await service.create_client(user_id, days=30)
except XuiAuthError as e:
    print(f"Ошибка авторизации: {e}")
except XuiClientError as e:
    print(f"Ошибка создания клиента: {e}")
except XuiError as e:
    print(f"Ошибка X-UI: {e}")
```

### Логирование

Все операции логируются через `loguru`:

```
2026-01-15 10:30:45 | INFO | X-UI login success: Амстердам
2026-01-15 10:30:46 | INFO | X-UI клиент создан: user_id=123456789, uuid=...
2026-01-15 10:31:00 | ERROR | X-UI delete client error: Connection timeout
```

## Безопасность

### Рекомендации

1. **Сильный пароль** для X-UI панели
2. **HTTPS** для API (вместо HTTP)
3. **Ограничение доступа** по IP (только сервер бота)
4. **Регулярная смена** паролей
5. **Не логировать** API ключи и пароли

### Хранение credentials

- Пароли хранятся в БД в таблице `servers`
- Не логируются и не выводятся в debug
- Передаются только через HTTPS

## Фоновые задачи

### Проверка истекших подписок

```python
from services.scheduler import check_expired_subscriptions

# Запускается каждый час
await check_expired_subscriptions()
```

### Синхронизация трафика

```python
from services.scheduler import sync_traffic_stats

# Запускается каждый час
await sync_traffic_stats()
```

## Мониторинг

### Проверка статуса серверов

```python
from services.xui_api import XuiServiceFactory

servers = await get_active_servers()

for server in servers:
    service = await XuiServiceFactory.get_service(server)
    
    if await service.check_connection():
        print(f"✅ {server['name']}: OK")
    else:
        print(f"❌ {server['name']}: OFFLINE")
```

## Troubleshooting

### Ошибка авторизации

```
X-UI login failed: 401
```

**Решение**: Проверьте логин/пароль, убедитесь что API доступен.

### Timeout при подключении

```
X-UI connection error: Connection timeout
```

**Решение**: Проверьте firewall, убедитесь что порт открыт.

### Клиент не создается

```
X-UI create client failed: 500
```

**Решение**: Проверьте inbound_id, убедитесь что inbound активен.

### Ключ не работает

**Решение**: 
1. Проверьте домен и порт
2. Убедитесь что TLS сертификат валиден
3. Проверьте настройки клиента (VLESS, TLS)

## Полезные ссылки

- [3X-UI Documentation](https://github.com/MHSanaei/3x-ui)
- [Xray Core](https://github.com/XTLS/Xray-core)
- [VLESS Protocol](https://github.com/XTLS/Xray-core/blob/main/docs/config/proxies/vless.md)

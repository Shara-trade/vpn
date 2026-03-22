# X-UI API Quick Reference

## Подключение

```python
from services.xui_api import XuiService

service = XuiService({
    "api_url": "http://IP:PORT",
    "api_username": "admin",
    "api_password": "password",
    "inbound_id": 1
})
```

## Методы XuiService

| Метод | Описание | Возвращает |
|-------|----------|------------|
| `login()` | Авторизация | `bool` |
| `check_connection()` | Проверка подключения | `bool` |
| `get_inbound()` | Получение inbound | `Dict` |
| `create_client(user_id, days, traffic_limit_gb)` | Создание клиента | `Dict` |
| `delete_client(uuid)` | Удаление клиента | `bool` |
| `update_client(uuid, days, enable, traffic_limit_gb)` | Обновление клиента | `bool` |
| `get_client_traffic(email)` | Статистика трафика | `Dict` |
| `get_all_clients()` | Все клиенты | `List[Dict]` |
| `reset_client_traffic(email)` | Сброс трафика | `bool` |
| `close()` | Закрытие сессии | `None` |

## Формат VLESS ключа

```
vless://{uuid}@{domain}:{port}?security=tls&type=tcp#{name}
```

Пример:
```
vless://8940e8e7-915d-4f78-9c4b-300eac0f7cdb@ams.freakvpn.ru:443?security=tls&type=tcp#FreakVPN_AMS
```

## Результат create_client()

```python
{
    "uuid": "8940e8e7-915d-4f78-9c4b-300eac0f7cdb",
    "key": "vless://...",
    "email": "user_123456789",
    "expires_at": datetime(2026, 4, 20),
    "traffic_limit": 0
}
```

## Результат get_client_traffic()

```python
{
    "up": 1073741824,      # байты
    "down": 5368709120,    # байты
    "total": 6442450944    # байты
}
```

## Утилиты vpn_utils

```python
from services.vpn_utils import (
    VlessKeyParser,      # Парсинг VLESS ключей
    VmessKeyParser,      # Парсинг VMess ключей
    KeyValidator,        # Валидация ключей
    KeyGenerator,        # Генерация ключей
    format_traffic,      # Форматирование трафика
    parse_traffic_limit  # Парсинг лимита трафика
)
```

### Примеры

```python
# Парсинг ключа
parsed = VlessKeyParser.parse(key)
# {"uuid": "...", "host": "...", "port": 443, ...}

# Валидация
is_valid, key_type = KeyValidator.validate(key)

# Генерация ключа
result = KeyGenerator.generate_vless_key(
    host="ams.freakvpn.ru",
    port=443,
    name="FreakVPN"
)

# Форматирование трафика
format_traffic(6442450944)  # "6.0 GB"
```

## Обработка ошибок

```python
from services.xui_api import (
    XuiError,        # Базовое исключение
    XuiAuthError,    # Ошибка авторизации
    XuiClientError   # Ошибка работы с клиентом
)

try:
    result = await service.create_client(user_id, days=30)
except XuiAuthError:
    # Проблемы с авторизацией
    pass
except XuiClientError:
    # Проблемы с созданием клиента
    pass
except XuiError:
    # Общая ошибка X-UI
    pass
```

## XuiServiceFactory

```python
from services.xui_api import XuiServiceFactory

# Получить сервис (Singleton)
service = await XuiServiceFactory.get_service(server)

# Получить по ID
service = await XuiServiceFactory.get_service_by_id(server_id)

# Закрыть все сессии
await XuiServiceFactory.close_all()

# Удалить из кэша
await XuiServiceFactory.remove_service(server_id)
```

## Быстрые функции

```python
from services.xui_api import (
    create_key_for_user,
    delete_key_for_user,
    check_server_connection
)

# Создать ключ
result = await create_key_for_user(server, user_id, days=30)

# Удалить ключ
await delete_key_for_user(server, uuid)

# Проверить сервер
is_ok = await check_server_connection(server)
```

## Тестирование

```bash
python test_xui_connection.py --url http://IP:PORT --user admin --pass password
```

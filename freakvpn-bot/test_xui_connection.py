"""
Тестовый скрипт для проверки подключения к X-UI API.

Использование:
    python test_xui_connection.py

Или с параметрами:
    python test_xui_connection.py --url http://1.2.3.4:54321 --user admin --pass password
"""

import asyncio
import argparse
import sys
from getpass import getpass

from services.xui_api import XuiService, XuiAuthError, XuiClientError
from services.vpn_utils import VlessKeyParser, format_traffic


async def test_connection(
    api_url: str,
    username: str,
    password: str,
    inbound_id: int = 1
):
    """
    Тестирование подключения к X-UI.
    
    Args:
        api_url: URL API (например, http://1.2.3.4:54321)
        username: Логин X-UI
        password: Пароль X-UI
        inbound_id: ID inbound
    """
    print("\n" + "=" * 60)
    print("🔌 Тестирование подключения к X-UI API")
    print("=" * 60)
    
    # Создаем тестовый сервер
    server = {
        "id": 0,
        "name": "Test Server",
        "domain": "test.example.com",
        "api_url": api_url,
        "api_username": username,
        "api_password": password,
        "inbound_id": inbound_id,
        "port": 443
    }
    
    service = XuiService(server)
    
    try:
        # 1. Проверка подключения
        print("\n1️⃣ Проверка подключения...")
        
        if await service.check_connection():
            print("   ✅ Подключение успешно!")
        else:
            print("   ❌ Не удалось подключиться к серверу")
            return
        
        # 2. Получение информации о inbound
        print("\n2️⃣ Получение информации о inbound...")
        
        inbound = await service.get_inbound()
        
        if inbound:
            print(f"   ✅ Inbound ID: {inbound.get('id')}")
            print(f"   📝 Port: {inbound.get('port')}")
            print(f"   🔐 Protocol: {inbound.get('protocol')}")
            
            # Парсим клиентов
            import json
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
            print(f"   👥 Клиентов на сервере: {len(clients)}")
        else:
            print("   ⚠️ Не удалось получить inbound")
        
        # 3. Тест создания клиента
        print("\n3️⃣ Тест создания клиента...")
        
        test_user_id = 999999999  # Тестовый ID
        test_days = 1  # 1 день для теста
        
        result = await service.create_client(
            user_id=test_user_id,
            days=test_days,
            traffic_limit_gb=0
        )
        
        if result:
            print("   ✅ Тестовый клиент создан!")
            print(f"   🔑 UUID: {result['uuid']}")
            print(f"   📧 Email: {result['email']}")
            print(f"   📅 Истекает: {result['expires_at']}")
            print(f"\n   🔐 VLESS ключ:")
            print(f"   {result['key']}")
            
            # Парсим ключ для проверки
            parsed = VlessKeyParser.parse(result['key'])
            if parsed:
                print(f"\n   📋 Параметры ключа:")
                print(f"      Host: {parsed['host']}")
                print(f"      Port: {parsed['port']}")
                print(f"      Security: {parsed['security']}")
                print(f"      Type: {parsed['type']}")
            
            # 4. Тест получения трафика
            print("\n4️⃣ Тест получения статистики...")
            
            traffic = await service.get_client_traffic(result['email'])
            
            if traffic:
                print(f"   ✅ Статистика получена")
                print(f"   📊 Трафик: {format_traffic(traffic['total'])}")
            else:
                print("   ⚠️ Не удалось получить статистику")
            
            # 5. Удаление тестового клиента
            print("\n5️⃣ Удаление тестового клиента...")
            
            if await service.delete_client(result['uuid']):
                print("   ✅ Тестовый клиент удален")
            else:
                print("   ⚠️ Не удалось удалить клиента (удалите вручную)")
        else:
            print("   ❌ Не удалось создать тестового клиента")
        
        print("\n" + "=" * 60)
        print("✅ Тестирование завершено успешно!")
        print("=" * 60 + "\n")
        
    except XuiAuthError as e:
        print(f"\n❌ Ошибка авторизации: {e}")
        print("   Проверьте логин и пароль")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        
    finally:
        await service.close()


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Тестирование подключения к X-UI API"
    )
    
    parser.add_argument(
        "--url",
        help="URL X-UI панели (например, http://1.2.3.4:54321)"
    )
    parser.add_argument(
        "--user",
        help="Логин X-UI"
    )
    parser.add_argument(
        "--pass",
        dest="password",
        help="Пароль X-UI"
    )
    parser.add_argument(
        "--inbound",
        type=int,
        default=1,
        help="ID inbound (по умолчанию: 1)"
    )
    
    args = parser.parse_args()
    
    # Получаем данные
    if args.url and args.user and args.password:
        api_url = args.url
        username = args.user
        password = args.password
    else:
        print("\n📋 Введите данные для подключения к X-UI:\n")
        api_url = input("URL панели (http://IP:PORT): ").strip()
        username = input("Логин: ").strip()
        password = getpass("Пароль: ").strip()
    
    # Запускаем тест
    asyncio.run(test_connection(
        api_url=api_url,
        username=username,
        password=password,
        inbound_id=args.inbound
    ))


if __name__ == "__main__":
    main()

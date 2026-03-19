"""
Планировщик фоновых задач.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from loguru import logger
import pytz

from config import TIMEZONE
from database.queries import (
    get_expiring_users, get_expired_users, update_user, get_all_users
)
from services.xui_api import delete_vpn_key
from database.queries import get_server_by_id


scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))


async def check_expiring_subscriptions():
    """
    Проверяет пользователей с истекающей подпиской.
    Отправляет уведомления за 3 дня до истечения.
    """
    logger.info("Проверка истекающих подписок...")
    
    users = await get_expiring_users(days=3)
    
    for user in users:
        if not user.expires_at:
            continue
        
        days_left = (user.expires_at - datetime.now()).days
        
        if days_left <= 3 and days_left > 0:
            # Здесь должна быть отправка уведомления пользователю
            # Нужно передать bot instance
            logger.info(f"Пользователь {user.user_id} - осталось {days_left} дней")


async def check_expired_subscriptions():
    """
    Проверяет пользователей с истёкшей подпиской.
    Блокирует доступ и удаляет ключи.
    """
    logger.info("Проверка истёкших подписок...")
    
    users = await get_expired_users()
    
    for user in users:
        # Удаляем ключ с сервера
        if user.server_id and user.key_uuid:
            server = await get_server_by_id(user.server_id)
            if server:
                await delete_vpn_key(server, user.user_id)
        
        # Обновляем статус
        await update_user(user.user_id, status="expired")
        
        logger.info(f"Подписка истекла: {user.user_id}")


async def sync_traffic_stats():
    """
    Синхронизирует статистику трафика с X-UI серверами.
    """
    logger.info("Синхронизация статистики трафика...")
    
    # Здесь должна быть логика получения статистики из X-UI
    # и обновления в базе данных


async def daily_backup():
    """
    Создаёт ежедневный бекап базы данных.
    """
    logger.info("Создание бекапа базы данных...")
    
    from config import DATABASE_PATH
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/freakvpn_{timestamp}.db"
    
    try:
        shutil.copy2(DATABASE_PATH, backup_path)
        logger.info(f"Бекап создан: {backup_path}")
    except Exception as e:
        logger.error(f"Ошибка создания бекапа: {e}")


def start_scheduler():
    """Запускает планировщик задач."""
    
    # Ежедневная проверка в 00:00 по Москве
    scheduler.add_job(
        check_expiring_subscriptions,
        CronTrigger(hour=0, minute=0),
        id="check_expiring"
    )
    
    # Ежедневная проверка истёкших в 00:05
    scheduler.add_job(
        check_expired_subscriptions,
        CronTrigger(hour=0, minute=5),
        id="check_expired"
    )
    
    # Каждые 6 часов - синхронизация трафика
    scheduler.add_job(
        sync_traffic_stats,
        CronTrigger(hour="*/6"),
        id="sync_traffic"
    )
    
    # Ежедневный бекап в 03:00
    scheduler.add_job(
        daily_backup,
        CronTrigger(hour=3, minute=0),
        id="daily_backup"
    )
    
    scheduler.start()
    logger.info("Планировщик задач запущен")


def stop_scheduler():
    """Останавливает планировщик."""
    scheduler.shutdown()
    logger.info("Планировщик задач остановлен")

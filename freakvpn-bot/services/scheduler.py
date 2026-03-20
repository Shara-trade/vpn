"""
Планировщик фоновых задач.
Проверка подписок, уведомления, синхронизация статистики.
"""

from datetime import datetime, timedelta
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pathlib import Path
import pytz
import shutil

from config import config
from database import queries, db
from services.xui_api import XuiService


class SchedulerService:
    """
    Сервис фоновых задач.
    """
    
    def __init__(self):
        """Инициализация планировщика."""
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(config.TIMEZONE))
        self._bot = None  # Будет установлен при запуске бота
    
    def set_bot(self, bot):
        """Установка экземпляра бота."""
        self._bot = bot
    
    def start(self):
        """Запуск планировщика."""
        # Ежедневная проверка подписок в 00:00 по Москве
        self.scheduler.add_job(
            self.check_expired_subscriptions,
            CronTrigger(hour=0, minute=0, timezone=config.TIMEZONE),
            id="check_expired",
            replace_existing=True
        )
        
        # Ежедневные уведомления о скором истечении в 12:00
        self.scheduler.add_job(
            self.notify_expiring_soon,
            CronTrigger(hour=12, minute=0, timezone=config.TIMEZONE),
            id="notify_expiring",
            replace_existing=True
        )
        
        # Ежечасная синхронизация статистики
        self.scheduler.add_job(
            self.sync_traffic_stats,
            CronTrigger(hour="*", timezone=config.TIMEZONE),
            id="sync_stats",
            replace_existing=True
        )
        
        # Ежедневный бекап БД в 03:00
        self.scheduler.add_job(
            self.backup_database,
            CronTrigger(hour=3, minute=0, timezone=config.TIMEZONE),
            id="backup_db",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Планировщик задач запущен")
    
    def stop(self):
        """Остановка планировщика."""
        self.scheduler.shutdown()
        logger.info("Планировщик задач остановлен")
    
    async def check_expired_subscriptions(self):
        """
        Проверка истекших подписок.
        Блокирует пользователей с истекшей подпиской и удаляет ключи.
        """
        logger.info("Запуск проверки истекших подписок")
        
        try:
            # Получаем пользователей с истекшей подпиской
            expired_users = await queries.get_expired_users()
            
            if not expired_users:
                logger.info("Нет пользователей с истекшей подпиской")
                return
            
            for user in expired_users:
                try:
                    # Удаляем ключ с сервера
                    if user.get("key_uuid") and user.get("server_id"):
                        server = await queries.get_server(user["server_id"])
                        
                        if server:
                            xui = XuiService(server)
                            await xui.delete_client(user["key_uuid"])
                    
                    # Блокируем пользователя
                    await queries.set_user_status(user["user_id"], "blocked")
                    
                    logger.info(
                        f"Подписка истекла: user_id={user['user_id']}"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Ошибка при обработке user_id={user['user_id']}: {e}"
                    )
            
            logger.info(f"Обработано {len(expired_users)} истекших подписок")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке подписок: {e}")
    
    async def notify_expiring_soon(self):
        """
        Уведомление пользователей о скором истечении подписки.
        """
        logger.info("Запуск уведомлений о скором истечении")
        
        if not self._bot:
            logger.error("Bot не установлен для планировщика")
            return
        
        try:
            # Получаем пользователей, у которых подписка истекает через 3 дня
            expiring_users = await queries.get_expiring_users(days=3)
            
            if not expiring_users:
                logger.info("Нет пользователей с истекающей подпиской")
                return
            
            sent = 0
            for user in expiring_users:
                try:
                    days_left = (user["expires_at"] - datetime.utcnow()).days
                    
                    await self._bot.send_message(
                        user["user_id"],
                        f"⚠️ Твоя подписка истекает через {days_left} дн.\n\n"
                        f"Не забудь продлить в разделе '💰 Купить / Продлить', "
                        f"чтобы не потерять доступ к VPN."
                    )
                    sent += 1
                    
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке уведомления user_id={user['user_id']}: {e}"
                    )
            
            logger.info(f"Отправлено {sent} уведомлений")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {e}")
    
    async def sync_traffic_stats(self):
        """
        Синхронизация статистики трафика пользователей.
        """
        logger.info("Запуск синхронизации трафика")
        
        try:
            # Получаем всех активных пользователей с серверами
            users = await db.fetchall(
                """
                SELECT u.user_id, u.key_uuid, u.server_id
                FROM users u
                WHERE u.status = 'active' 
                AND u.key_uuid IS NOT NULL 
                AND u.server_id IS NOT NULL
                """
            )
            
            if not users:
                return
            
            # Группируем по серверам
            servers_cache = {}
            
            for user in users:
                server_id = user["server_id"]
                
                if server_id not in servers_cache:
                    server = await queries.get_server(server_id)
                    servers_cache[server_id] = server
                else:
                    server = servers_cache[server_id]
                
                if not server:
                    continue
                
                try:
                    xui = XuiService(server)
                    
                    # Получаем статистику по UUID клиента
                    traffic = await xui.get_client_traffic_by_uuid(user["key_uuid"])
                    
                    if traffic:
                        total_traffic = traffic.get("up", 0) + traffic.get("down", 0)
                        
                        # Обновляем в БД
                        await db.execute(
                            "UPDATE users SET traffic_used = ? WHERE user_id = ?",
                            (total_traffic, user["user_id"])
                        )
                    
                except Exception as e:
                    logger.error(
                        f"Ошибка при синхронизации user_id={user['user_id']}: {e}"
                    )
            
            logger.info(f"Синхронизирован трафик для {len(users)} пользователей")
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации трафика: {e}")

    async def backup_database(self):
        """
        Создание резервной копии базы данных.
        """
        logger.info("Запуск резервного копирования БД")

        try:
            # Путь к БД
            db_path = Path(config.DATABASE_PATH)
            
            if not db_path.exists():
                logger.warning(f"Файл БД не найден: {db_path}")
                return
            
            # Создаем папку для бекапов
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            # Имя файла бекапа
            backup_name = f"freakvpn_{datetime.now():%Y%m%d_%H%M%S}.db"
            backup_path = backup_dir / backup_name
            
            # Копируем файл
            shutil.copy2(db_path, backup_path)
            
            # Удаляем старые бекапы (оставляем последние 7)
            backups = sorted(backup_dir.glob("freakvpn_*.db"), reverse=True)
            for old_backup in backups[7:]:
                old_backup.unlink()
                logger.debug(f"Удален старый бекап: {old_backup}")
            
            logger.info(f"Бекап создан: {backup_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при создании бекапа: {e}")


# Глобальный экземпляр планировщика
scheduler = SchedulerService()

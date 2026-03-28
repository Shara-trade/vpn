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
        
        # Ежечасная проверка автопродления ключей
        self.scheduler.add_job(
            self.check_autorenew_keys,
            CronTrigger(minute=0, timezone=config.TIMEZONE),
            id="check_autorenew",
            replace_existing=True
        )
        
        # Синхронизация трафика каждую минуту
        self.scheduler.add_job(
            self.sync_traffic_stats,
            CronTrigger(minute="*", timezone=config.TIMEZONE),
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
        Проверка истекших ключей.
        Удаляет истекшие ключи с серверов.
        """
        logger.info("Запуск проверки истекших ключей")
        
        try:
            # Получаем истекшие ключи из новой таблицы
            expired_keys = await queries.get_expired_keys()
            
            if not expired_keys:
                logger.info("Нет истекших ключей")
                return
            
            for key in expired_keys:
                try:
                    # Удаляем ключ с сервера
                    if key.get("key_uuid") and key.get("server_id"):
                        server = await queries.get_server(key["server_id"])
                        
                        if server:
                            xui = XuiService(server)
                            await xui.delete_client(key["key_uuid"])
                            await queries.decrement_server_load(key["server_id"])
                    
                    # Деактивируем ключ
                    await queries.delete_user_key(key["id"])
                    
                    logger.info(
                        f"Ключ истек: key_id={key['id']}, user_id={key['user_id']}"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Ошибка при обработке key_id={key['id']}: {e}"
                    )
            
            logger.info(f"Обработано {len(expired_keys)} истекших ключей")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке ключей: {e}")
    
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
                        f"Не забудь продлить в разделе 'Купить', "
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
    
    async def check_autorenew_keys(self):
        """
        Проверка ключей с автопродлением.
        Ключи истекающие в течение 12 часов продлеваются автоматически.
        """
        logger.info("Запуск проверки автопродления ключей")
        
        try:
            # Получаем ключи с автопродлением, истекающие в течение 12 часов
            expiring_keys = await queries.get_expiring_keys(hours=12)
            
            if not expiring_keys:
                logger.info("Нет ключей для автопродления")
                return
            
            # Получаем цену 30-дневного тарифа для автопродления
            tariffs = await queries.get_tariffs()
            renew_price = 29900  # 默认 299₽
            renew_days = 30
            
            for tariff in tariffs:
                if tariff.get("months") == 1:
                    renew_price = tariff["price"]
                    renew_days = tariff.get("days", 30)
                    break
            
            renewed = 0
            failed = 0
            
            for key_data in expiring_keys:
                try:
                    user_id = key_data["user_id"]
                    key_id = key_data["id"]
                    
                    # Получаем пользователя и баланс
                    user = await queries.get_user(user_id)
                    if not user:
                        continue
                    
                    balance = user.get("balance", 0)
                    
                    # Проверяем баланс
                    if balance < renew_price:
                        logger.info(f"Недостаточно средств для автопродления key_id={key_id}")
                        failed += 1
                        
                        # Отправляем уведомление
                        if self._bot:
                            try:
                                await self._bot.send_message(
                                    user_id,
                                    f"⚠️ Автопродление невозможно: недостаточно средств.\n"
                                    f"Баланс: {balance // 100}₽, требуется: {renew_price // 100}₽\n"
                                    f"Пополните баланс для продления ключа."
                                )
                            except:
                                pass
                        
                        # Отключаем автопродление
                        await queries.set_key_auto_renew(key_id, False)
                        continue
                    
                    # Списываем средства
                    new_balance = await queries.update_user_balance(user_id, -renew_price)
                    
                    # Продлеваем ключ
                    new_expires = datetime.utcnow() + timedelta(days=renew_days)
                    await queries.update_key_expires(key_id, new_expires)
                    
                    # Продлеваем на сервере
                    server = await queries.get_server(key_data["server_id"])
                    if server:
                        xui = XuiService(server)
                        await xui.update_client_expiry(key_data["key_uuid"], renew_days)
                    
                    # Логируем
                    await queries.create_transaction(
                        user_id=user_id,
                        amount=-renew_price,
                        transaction_type="autorenew",
                        description=f"Автопродление ключа на {renew_days} дней"
                    )
            
                    await queries.add_log(
                        category="payment",
                        action="autorenew",
                        user_id=user_id,
                        amount=renew_price,
                        details={"key_id": key_id, "days": renew_days}
                    )
                    
                    # Отправляем уведомление
                    if self._bot:
                        try:
                            await self._bot.send_message(
                                user_id,
                                f"✅ Автопродление выполнено!\n\n"
                                f"Списано: {renew_price // 100}₽\n"
                                f"Баланс: {new_balance // 100}₽\n"
                                f"Новый срок: {new_expires.strftime('%d.%m.%Y')}"
                            )
                        except:
                            pass
                    
                    renewed += 1
                    logger.info(f"Автопродлен ключ key_id={key_id} для user_id={user_id}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при автопродлении key_id={key_data.get('id')}: {e}")
                    failed += 1
            
            logger.info(f"Автопродление: успешно={renewed}, неудачно={failed}")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке автопродления: {e}")
    
    async def sync_traffic_stats(self):
        """
        Синхронизация статистики трафика пользователей.
        Обновляет traffic_used в users (суммарно по всем ключам).
        """
        logger.info("Запуск синхронизации трафика")
        
        try:
            # Получаем все активные ключи из user_keys
            keys = await db.fetchall(
                """
                SELECT uk.id, uk.user_id, uk.key_uuid, uk.server_id
                FROM user_keys uk
                WHERE uk.is_active = 1 AND uk.key_uuid IS NOT NULL
                """
            )
            
            if not keys:
                return
            
            # Группируем трафик по пользователям
            user_traffic = {}
            servers_cache = {}
            
            for key in keys:
                server_id = key["server_id"]
                user_id = key["user_id"]
                key_uuid = key["key_uuid"]
                
                # Получаем сервер
                if server_id not in servers_cache:
                    server = await queries.get_server(server_id)
                    servers_cache[server_id] = server
                else:
                    server = servers_cache[server_id]
                
                if not server:
                    continue
                
                try:
                    xui = XuiService(server)
                    traffic = await xui.get_client_traffic_by_uuid(key_uuid)
                    
                    if traffic:
                        total_traffic = traffic.get("up", 0) + traffic.get("down", 0)
                        
                        if user_id not in user_traffic:
                            user_traffic[user_id] = 0
                        user_traffic[user_id] += total_traffic
                    
                except Exception as e:
                    logger.debug(f"Ошибка при синхронизации key_id={key['id']}: {e}")
            
            # Обновляем трафик в БД
            for user_id, traffic in user_traffic.items():
                await db.execute(
                    "UPDATE users SET traffic_used = ? WHERE user_id = ?",
                    (traffic, user_id)
                )
            
            logger.info(f"Синхронизирован трафик для {len(user_traffic)} пользователей")
            
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

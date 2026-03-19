"""
FreakVPN Bot - Telegram бот для продажи VPN-доступа.
"""
import asyncio
import sys
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, LOG_LEVEL, TIMEZONE


def setup_logging():
    """Настройка логирования."""
    logger.remove()
    
    # Логирование в файл
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    # Логирование в консоль
    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


async def main():
    """Главная функция запуска бота."""
    setup_logging()
    logger.info("Запуск FreakVPN Bot...")
    
    # Проверка токена
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не указан в .env файле!")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация middleware
    from middlewares.registration import RegistrationMiddleware
    from middlewares.throttle import ThrottlingMiddleware
    
    dp.message.middleware(RegistrationMiddleware())
    dp.callback_query.middleware(RegistrationMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    
    # Инициализация базы данных
    from database import init_db
    await init_db()
    logger.info("База данных инициализирована")
    
    # Регистрация роутеров
    from handlers import start, menu, profile, key, purchase, servers, support, callbacks, admin
    
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(menu.router)
    dp.include_router(profile.router)
    dp.include_router(key.router)
    dp.include_router(purchase.router)
    dp.include_router(servers.router)
    dp.include_router(support.router)
    dp.include_router(callbacks.router)
    
    # Запуск планировщика
    from services.scheduler import start_scheduler
    start_scheduler()
    logger.info("Планировщик задач запущен")
    
    # Запуск бота
    logger.info("Бот запущен и готов к работе")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")

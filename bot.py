"""
Точка входа в бота StarinaVPN.
"""

import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from loguru import logger

from config import config
from database import init_db
from middlewares import RegistrationMiddleware, ThrottleMiddleware
from middlewares.blocked import BlockedUserMiddleware


async def set_commands(bot: Bot) -> None:
    """Установка команд бота для отображения в меню."""
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Справка по использованию"),
        BotCommand(command="profile", description="Мой профиль и баланс"),
        BotCommand(command="key", description="Мой VPN ключ"),
        BotCommand(command="support", description="Связь с поддержкой"),
        BotCommand(command="menu", description="Главное меню"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота зарегистрированы")


def setup_logging() -> None:
    """Настройка логирования."""
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем обработчик для консоли
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )
    
    # Добавляем обработчик для файла с ротацией
    log_path = Path("logs") / "bot.log"
    log_path.parent.mkdir(exist_ok=True)
    
    logger.add(
        log_path,
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )


async def main() -> None:
    """Главная функция запуска бота."""
    # Настраиваем логирование
    setup_logging()
    
    logger.info("Запуск StarinaVPN бота...")
    
    # Проверяем конфигурацию
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return
    
    # Инициализируем бота и диспетчер
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрируем middleware (порядок важен!)
    dp.update.middleware(RegistrationMiddleware())
    dp.update.middleware(BlockedUserMiddleware())
    dp.update.middleware(ThrottleMiddleware(rate_limit=0.5, burst_limit=5))
    
    # Инициализируем базу данных
    await init_db()
    
    # Устанавливаем команды бота
    await set_commands(bot)
    
    # Регистрируем роутеры (хендлеры)
    from handlers import start, menu, profile, key, purchase, callbacks, admin
    
    # Важен порядок: admin должен быть первым для обработки /admin
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(profile.router)
    dp.include_router(key.router)
    dp.include_router(purchase.router)
    dp.include_router(callbacks.router)
    
    # Запускаем планировщик
    from services.scheduler import scheduler
    scheduler.set_bot(bot)
    scheduler.start()
    
    logger.info("Бот успешно запущен!")
    
    # Запускаем polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.stop()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")

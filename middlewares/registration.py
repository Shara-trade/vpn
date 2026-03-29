"""
Middleware для автоматической регистрации пользователей.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from loguru import logger

from database import queries
from utils.helpers import generate_referral_code


class RegistrationMiddleware(BaseMiddleware):
    """
    Middleware для автоматической регистрации новых пользователей.
    Выполняется перед каждым обновлением.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Выполнение middleware.
        
        Args:
            handler: Следующий обработчик
            event: Событие Telegram
            data: Данные контекста
            
        Returns:
            Результат выполнения обработчика
        """
        # Получаем пользователя из события
        user: User = data.get("event_from_user")
        
        if user:
            # Проверяем, существует ли пользователь
            db_user = await queries.get_user(user.id)
            
            if db_user is None:
                # Создаем нового пользователя
                referral_code = generate_referral_code(user.id)
                
                await queries.create_user(
                    user_id=user.id,
                    full_name=user.full_name,
                    username=user.username,
                    referral_code=referral_code
                )
                
                logger.info(
                    f"Новый пользователь: {user.id} | {user.full_name} | @{user.username}"
                )
                
                # Получаем созданного пользователя
                db_user = await queries.get_user(user.id)
            
            # Обновляем время последней активности
            await queries.update_user_activity(user.id)
            
            # Добавляем пользователя в контекст
            data["db_user"] = db_user
        
        # Продолжаем выполнение
        return await handler(event, data)

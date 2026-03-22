"""
Middleware для блокировки пользователей.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger


class BlockedUserMiddleware(BaseMiddleware):
    """
    Middleware для блокировки пользователей.
    Проверяет статус пользователя перед обработкой запроса.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Выполнение middleware.
        """
        db_user = data.get("db_user")
        
        if db_user and db_user.get("status") == "blocked":
            if isinstance(event, Message):
                # Игнорируем команду /start для заблокированных
                if event.text and event.text.startswith("/start"):
                    return await handler(event, data)
                
                await event.answer(
                    "🚫 Ваш доступ к StarinaVPN заблокирован.\n\n"
                    "Для восстановления доступа обратитесь к администратору: @StarinaVPN_Support"
                )
                return None
                
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "🚫 Ваш доступ заблокирован",
                    show_alert=True
                )
                return None
        
        return await handler(event, data)

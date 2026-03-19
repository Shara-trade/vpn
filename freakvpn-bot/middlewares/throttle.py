"""
Middleware для защиты от спама (throttling).
"""
from typing import Callable, Any, Awaitable
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from utils.constants import ERROR_GENERIC


class ThrottlingMiddleware(BaseMiddleware):
    """Защита от спама с ограничением частоты запросов."""
    
    def __init__(self, rate_limit: float = 0.5):
        """
        Args:
            rate_limit: Минимальное время между запросами в секундах
        """
        self.rate_limit = rate_limit
        self.user_last_request: dict[int, datetime] = {}
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.now()
        
        # Проверяем время последнего запроса
        last_request = self.user_last_request.get(user_id)
        
        if last_request:
            time_diff = (now - last_request).total_seconds()
            
            if time_diff < self.rate_limit:
                # Слишком частые запросы
                return
        
        # Обновляем время последнего запроса
        self.user_last_request[user_id] = now
        
        # Очищаем старые записи
        self._cleanup_old_records()
        
        return await handler(event, data)
    
    def _cleanup_old_records(self):
        """Очищает старые записи для экономии памяти."""
        now = datetime.now()
        threshold = timedelta(minutes=5)
        
        self.user_last_request = {
            user_id: last_time
            for user_id, last_time in self.user_last_request.items()
            if (now - last_time) < threshold
        }

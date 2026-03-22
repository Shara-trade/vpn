"""
Middleware для защиты от спама (throttling).
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from collections import defaultdict
from datetime import datetime, timedelta
from loguru import logger


class ThrottleMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама.
    Ограничивает частоту запросов от пользователя.
    """
    
    def __init__(
        self,
        rate_limit: float = 0.5,
        burst_limit: int = 3,
        burst_window: int = 5
    ):
        """
        Инициализация middleware.
        
        Args:
            rate_limit: Минимальный интервал между запросами в секундах
            burst_limit: Максимальное количество запросов в окне
            burst_window: Временное окно в секундах для burst_limit
        """
        self.rate_limit = rate_limit
        self.burst_limit = burst_limit
        self.burst_window = burst_window
        
        # Хранилище последних запросов: user_id -> list of timestamps
        self._requests: Dict[int, list] = defaultdict(list)
        
        # Хранилище предупреждений: user_id -> count
        self._warnings: Dict[int, int] = defaultdict(int)
    
    def _cleanup_old_requests(self, user_id: int) -> None:
        """
        Удаление старых записей из истории запросов.
        
        Args:
            user_id: ID пользователя
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self.burst_window)
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] 
            if ts > cutoff
        ]
    
    def _is_rate_limited(self, user_id: int) -> bool:
        """
        Проверка, превышен ли лимит запросов.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если запрос следует отклонить
        """
        now = datetime.utcnow()
        
        # Очищаем старые записи
        self._cleanup_old_requests(user_id)
        
        # Проверяем burst limit
        if len(self._requests[user_id]) >= self.burst_limit:
            return True
        
        # Проверяем rate limit
        if self._requests[user_id]:
            last_request = self._requests[user_id][-1]
            if (now - last_request).total_seconds() < self.rate_limit:
                return True
        
        # Добавляем текущий запрос
        self._requests[user_id].append(now)
        return False
    
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
        # Получаем user_id из события
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        # Проверяем лимит
        if user_id and self._is_rate_limited(user_id):
            self._warnings[user_id] += 1
            
            if self._warnings[user_id] <= 3:
                # Показываем предупреждение только первые 3 раза
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "⚠️ Слишком много запросов. Подождите немного.",
                        show_alert=True
                    )
                elif isinstance(event, Message):
                    await event.answer(
                        "⚠️ Слишком много запросов. Подождите немного."
                    )
            
            logger.warning(f"Rate limited: user_id={user_id}")
            return None
        
        # Сбрасываем счетчик предупреждений при успешном запросе
        if user_id:
            self._warnings[user_id] = 0
        
        # Продолжаем выполнение
        return await handler(event, data)

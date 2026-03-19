"""
Middleware для автоматической регистрации пользователей.
"""
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from loguru import logger

from database.queries import get_user_by_id, create_user, update_last_activity
from config import ADMIN_IDS


class RegistrationMiddleware(BaseMiddleware):
    """Автоматическая регистрация новых пользователей."""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        # Получаем user_id
        user = event.from_user
        user_id = user.id
        
        # Проверяем, существует ли пользователь
        db_user = await get_user_by_id(user_id)
        
        if db_user is None:
            # Создаём нового пользователя
            username = user.username
            full_name = user.full_name
            
            # Проверяем реферальный код (если есть)
            referral_code = None
            if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                parts = event.text.split()
                if len(parts) > 1 and parts[1].startswith("ref"):
                    referral_code = parts[1]
            
            # Определяем пригласившего
            referred_by = None
            if referral_code:
                from database.queries import get_user_by_referral_code
                referrer = await get_user_by_referral_code(referral_code)
                if referrer and referrer.user_id != user_id:
                    referred_by = referrer.user_id
            
            # Проверяем, админ ли
            is_admin = user_id in ADMIN_IDS
            
            db_user = await create_user(
                user_id=user_id,
                username=username,
                full_name=full_name,
                referred_by=referred_by
            )
            
            # Если админ, обновляем флаг
            if is_admin:
                from database.queries import update_user
                await update_user(user_id, is_admin=True)
                db_user.is_admin = True
            
            logger.info(f"Новый пользователь: {user_id} (@{username}, {full_name})")
            
            # Создаём реферальную связь
            if referred_by:
                from database.queries import create_referral
                await create_referral(referred_by, user_id)
                logger.info(f"Реферальная связь: {referred_by} -> {user_id}")
        else:
            # Обновляем время последней активности
            await update_last_activity(user_id)
        
        # Передаём пользователя в данные
        data["user"] = db_user
        
        return await handler(event, data)

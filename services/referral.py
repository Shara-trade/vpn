"""
Сервис для работы с реферальной системой.
"""

from typing import Optional
from database import queries, db
from config import config
from loguru import logger


class ReferralService:
    """
    Сервис для работы с рефералами.
    """
    
    @staticmethod
    async def process_referral(
        referrer_id: int,
        referral_id: int
    ) -> bool:
        """
        Обработка реферальной связи.
        
        Args:
            referrer_id: ID пригласившего
            referral_id: ID приглашенного
            
        Returns:
            True если успешно
        """
        try:
            # Проверяем, что это не один и тот же пользователь
            if referrer_id == referral_id:
                return False
            
            # Проверяем, что реферал еще не был обработан
            existing = await db.fetchone(
                "SELECT id FROM referrals WHERE referral_id = ?",
                (referral_id,)
            )
            
            if existing:
                return False
            
            # Создаем реферальную связь
            await queries.create_referral(referrer_id, referral_id)
            
            # Начисляем бонус пригласившему
            bonus = config.DEFAULT_REFERRAL_BONUS
            await queries.update_user_balance(referrer_id, bonus)
            
            # Обновляем заработок с рефералов
            referrer = await queries.get_user(referrer_id)
            if referrer:
                await db.execute(
                    "UPDATE users SET referral_earnings = ? WHERE user_id = ?",
                    (referrer.get("referral_earnings", 0) + bonus, referrer_id)
                )
            
            # Отмечаем, что бонус выплачен
            await queries.set_referral_bonus_paid(referral_id)
            
            # Создаем транзакцию
            await queries.create_transaction(
                user_id=referrer_id,
                amount=bonus,
                transaction_type="referral",
                description=f"Реферальный бонус за пользователя {referral_id}"
            )
            
            logger.info(
                f"Реферал обработан: referrer={referrer_id}, referral={referral_id}, bonus={bonus}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке реферала: {e}")
            return False
    
    @staticmethod
    async def get_referral_link(user_id: int, bot_username: str) -> str:
        """
        Получение реферальной ссылки пользователя.
        
        Args:
            user_id: ID пользователя
            bot_username: Username бота
            
        Returns:
            Реферальная ссылка
        """
        user = await queries.get_user(user_id)
        
        if user and user.get("referral_code"):
            return f"https://t.me/{bot_username}?start={user['referral_code']}"
        
        return f"https://t.me/{bot_username}"
    
    @staticmethod
    async def get_referral_stats(user_id: int) -> dict:
        """
        Получение статистики рефералов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        stats = await queries.get_referral_stats(user_id)
        
        return {
            "count": stats.get("referrals_count", 0),
            "earnings": stats.get("referral_earnings", 0)
        }

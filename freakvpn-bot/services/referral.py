"""
Сервис реферальной системы.
"""
from database.models import User
from database.queries import (
    get_user_by_referral_code, create_referral, update_user,
    create_transaction, mark_referral_bonus_paid, get_user_referrals
)
from config import DEFAULT_REFERRAL_BONUS
from utils.helpers import to_kopecks
from loguru import logger


async def process_referral_bonus(referrer_id: int, referral_id: int, bonus_amount: int = None):
    """
    Обрабатывает бонус за реферала после его первой покупки.
    
    Args:
        referrer_id: ID пригласившего
        referral_id: ID приглашённого
        bonus_amount: Сумма бонуса в копейках (по умолчанию из настроек)
    """
    if bonus_amount is None:
        bonus_amount = DEFAULT_REFERRAL_BONUS
    
    # Получаем реферальную связь
    referrals = await get_user_referrals(referrer_id)
    
    referral = None
    for r in referrals:
        if r.referral_id == referral_id and not r.bonus_paid:
            referral = r
            break
    
    if not referral:
        return False
    
    # Начисляем бонус
    referrer = await get_user_by_referral_code(f"ref{referrer_id}")
    if not referrer:
        return False
    
    new_balance = referrer.balance + bonus_amount
    new_earnings = referrer.referral_earnings + bonus_amount
    
    await update_user(
        referrer.user_id,
        balance=new_balance,
        referral_earnings=new_earnings
    )
    
    # Отмечаем, что бонус выплачен
    await mark_referral_bonus_paid(referral.id)
    
    # Создаём транзакцию
    await create_transaction(
        user_id=referrer.user_id,
        amount=bonus_amount,
        transaction_type="referral",
        description=f"Реферальный бонус за пользователя {referral_id}"
    )
    
    logger.info(f"Реферальный бонус {bonus_amount} коп. начислен пользователю {referrer_id}")
    
    return True


async def get_referral_stats(user_id: int) -> dict:
    """
    Возвращает статистику рефералов пользователя.
    
    Args:
        user_id: Telegram ID пользователя
    
    Returns:
        Словарь со статистикой
    """
    referrals = await get_user_referrals(user_id)
    
    total_referrals = len(referrals)
    active_referrals = 0
    total_earned = 0
    
    for ref in referrals:
        if ref.bonus_paid:
            total_earned += DEFAULT_REFERRAL_BONUS
        
        # Проверяем активность реферала
        from database.queries import get_user_by_id
        referral_user = await get_user_by_id(ref.referral_id)
        
        if referral_user and referral_user.is_active:
            active_referrals += 1
    
    return {
        "total_referrals": total_referrals,
        "active_referrals": active_referrals,
        "total_earned": total_earned
    }

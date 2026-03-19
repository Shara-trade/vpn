"""
Сервис платежей.
"""
from typing import Optional
from loguru import logger

from database.models import User
from database.queries import update_user, create_transaction


async def add_balance(
    user_id: int,
    amount_kopecks: int,
    admin_id: Optional[int] = None,
    description: str = "Пополнение баланса"
) -> bool:
    """
    Добавляет средства на баланс пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        amount_kopecks: Сумма в копейках
        admin_id: ID администратора (если пополнение от админа)
        description: Описание операции
    
    Returns:
        True если успешно
    """
    from database.queries import get_user_by_id
    
    user = await get_user_by_id(user_id)
    
    if not user:
        logger.error(f"Пользователь {user_id} не найден")
        return False
    
    new_balance = user.balance + amount_kopecks
    
    await update_user(user_id, balance=new_balance)
    
    transaction_type = "admin" if admin_id else "payment"
    
    await create_transaction(
        user_id=user_id,
        amount=amount_kopecks,
        transaction_type=transaction_type,
        description=description,
        admin_id=admin_id
    )
    
    logger.info(f"Баланс пользователя {user_id} пополнен на {amount_kopecks} коп.")
    
    return True


async def deduct_balance(
    user_id: int,
    amount_kopecks: int,
    description: str
) -> bool:
    """
    Списывает средства с баланса пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        amount_kopecks: Сумма в копейках
        description: Описание операции
    
    Returns:
        True если успешно
    """
    from database.queries import get_user_by_id
    
    user = await get_user_by_id(user_id)
    
    if not user:
        return False
    
    if user.balance < amount_kopecks:
        logger.warning(f"Недостаточно средств у пользователя {user_id}")
        return False
    
    new_balance = user.balance - amount_kopecks
    
    await update_user(user_id, balance=new_balance)
    
    await create_transaction(
        user_id=user_id,
        amount=-amount_kopecks,
        transaction_type="purchase",
        description=description
    )
    
    logger.info(f"Списано {amount_kopecks} коп. с баланса пользователя {user_id}")
    
    return True


async def check_balance(user_id: int, amount_kopecks: int) -> bool:
    """
    Проверяет, достаточно ли средств на балансе.
    
    Args:
        user_id: Telegram ID пользователя
        amount_kopecks: Требуемая сумма в копейках
    
    Returns:
        True если достаточно средств
    """
    from database.queries import get_user_by_id
    
    user = await get_user_by_id(user_id)
    
    if not user:
        return False
    
    return user.balance >= amount_kopecks

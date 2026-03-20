"""
Сервис для работы с платежами.
В текущей версии - заглушка, оплата через админа.
"""

from typing import Optional
from database import queries
from loguru import logger


class PaymentService:
    """
    Сервис для работы с платежами.
    
    В текущей реализации пользователь оплачивает через админа.
    Админ вручную пополняет баланс.
    """
    
    @staticmethod
    async def add_balance(
        user_id: int,
        amount: int,
        admin_id: int,
        description: str = None
    ) -> bool:
        """
        Начисление баланса пользователю от админа.
        
        Args:
            user_id: ID пользователя
            amount: Сумма в копейках
            admin_id: ID администратора
            description: Описание
            
        Returns:
            True если успешно
        """
        try:
            # Начисляем баланс
            new_balance = await queries.update_user_balance(user_id, amount)
            
            # Создаем транзакцию
            await queries.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type="admin",
                description=description or "Пополнение от администратора",
                admin_id=admin_id
            )
            
            logger.info(
                f"Баланс пополнен: user_id={user_id}, amount={amount}, "
                f"admin_id={admin_id}, new_balance={new_balance}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при начислении баланса: {e}")
            return False
    
    @staticmethod
    async def get_payment_instructions(amount: int) -> str:
        """
        Получение инструкции для оплаты.
        
        Args:
            amount: Сумма в копейках
            
        Returns:
            Текст инструкции
        """
        amount_rub = amount / 100
        
        return f"""💳 Пополнение баланса

Сумма: {amount_rub:.0f} ₽

Для пополнения баланса:
1. Напиши @FreakVPN_Shop
2. Укажи сумму: {amount_rub:.0f} ₽
3. Получи реквизиты для оплаты
4. Оплати и отправь чек

Баланс будет пополнен в течение часа после подтверждения оплаты.

🆔 Твой ID: понадобится при оплате"""

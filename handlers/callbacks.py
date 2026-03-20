"""
Общие callback-обработчики.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import queries
from utils.constants import SUPPORT_MESSAGE, BOT_NAME
from keyboards import get_support_keyboard

router = Router()


@router.callback_query(F.data == "show_faq")
async def callback_show_faq(callback: CallbackQuery):
    """Показ FAQ."""
    faq_text = """📌 Часто задаваемые вопросы

❓ Не подключается VPN?
→ Проверь правильность ключа
→ Попробуй другой сервер
→ Перезапусти приложение
→ Проверь интернет-соединение

❓ Как пополнить баланс?
→ Напиши @FreakVPN_Shop
→ Укажи сумму и получи реквизиты
→ После оплаты баланс пополнится в течение часа

❓ Как продлить подписку?
→ Зайди в "Купить / Продлить"
→ Выбери тариф
→ Подтверди покупку

❓ Можно ли использовать на нескольких устройствах?
→ Да, один ключ можно использовать 
  на нескольких устройствах одновременно

❓ Как сменить сервер?
→ Зайди в "Мой ключ"
→ Нажми "Сменить сервер"
→ Выбери новую локацию

❓ Что делать, если ключ не работает?
→ Напиши в поддержку @FreakVPN_Support
→ Пришли свой ID и описание проблемы"""
    
    await callback.message.edit_text(faq_text)
    await callback.answer()


@router.callback_query(F.data == "back_to_support")
async def callback_back_to_support(callback: CallbackQuery):
    """Возврат в поддержку."""
    await callback.message.edit_text(
        SUPPORT_MESSAGE.format(bot_name=BOT_NAME),
        reply_markup=get_support_keyboard()
    )
    await callback.answer()

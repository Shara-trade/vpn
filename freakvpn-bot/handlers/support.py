"""
Хендлер поддержки.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import SUPPORT_CONTACT, PAYMENT_CONTACT, BOT_NAME
from database.models import User
from keyboards.inline import get_support_keyboard
from utils.constants import SUPPORT_INFO

router = Router()


async def show_support(message: Message, user: User):
    """Показывает раздел поддержки."""
    text = SUPPORT_INFO.format(
        bot_name=BOT_NAME,
        payment_contact=PAYMENT_CONTACT,
        support_contact=SUPPORT_CONTACT
    )
    
    await message.answer(
        text,
        reply_markup=get_support_keyboard(SUPPORT_CONTACT, PAYMENT_CONTACT)
    )


@router.callback_query(F.data == "show_faq")
async def cb_show_faq(callback: CallbackQuery, user: User):
    """Показывает FAQ."""
    text = """📱 Часто задаваемые вопросы

❓ Как подключиться?
→ Скачай приложение v2RayTun
→ Скопируй ключ из раздела "Мой ключ"
→ Вставь ключ в приложение
→ Нажми "Подключить"

❓ Не работает подключение?
→ Проверь правильность ключа
→ Попробуй сменить сервер
→ Перезапусти приложение
→ Проверь интернет-соединение

❓ Как пополнить баланс?
→ Напиши @FreakVPN_Shop
→ Укажи свой ID и сумму
→ Оплати по реквизитам
→ Дождись зачисления (обычно до 1 часа)

❓ Как продлить подписку?
→ Зайди в "Купить / Продлить"
→ Выбери тариф
→ Подтверди покупку

❓ Что такое реферальная программа?
→ Приглашай друзей по своей ссылке
→ Получай бонус за каждую их покупку
→ Бонус зачисляется на баланс

❓ Как сменить сервер?
→ Зайди в "Мой ключ"
→ Нажми "Сменить сервер"
→ Выбери новый сервер
→ Получи новый ключ"""
    
    await callback.message.edit_text(text)
    await callback.answer()

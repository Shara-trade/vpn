"""
Общие callback-обработчики.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from loguru import logger

from config import config
from database import queries
from utils.constants import SUPPORT_MESSAGE, BOT_NAME
from utils.helpers import format_balance
from keyboards import get_support_keyboard

router = Router()


@router.callback_query(F.data == "close_message")
async def callback_close_message(callback: CallbackQuery):
    """Удаление сообщения по кнопке закрыть."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, db_user: dict = None):
    """Возврат в главное меню."""
    await callback.message.delete()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "back_to_key")
async def callback_back_to_key(callback: CallbackQuery, db_user: dict = None):
    """Возврат в раздел ключа."""
    await callback.message.delete()
    from handlers.key import show_key
    await show_key(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "back_to_profile")
async def callback_back_to_profile(callback: CallbackQuery, db_user: dict = None):
    """Возврат в профиль."""
    await callback.message.delete()
    from handlers.profile import show_profile
    await show_profile(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "back_to_tariffs")
async def callback_back_to_tariffs(callback: CallbackQuery, db_user: dict = None):
    """Возврат к списку тарифов."""
    await callback.message.delete()
    from handlers.purchase import show_tariffs
    await show_tariffs(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "go_to_key")
async def callback_go_to_key(callback: CallbackQuery, db_user: dict = None):
    """Переход в раздел ключа."""
    await callback.message.delete()
    from handlers.key import show_key
    await show_key(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "go_to_profile")
async def callback_go_to_profile(callback: CallbackQuery, db_user: dict = None):
    """Переход в профиль."""
    await callback.message.delete()
    from handlers.profile import show_profile
    await show_profile(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "check_payment")
async def callback_check_payment(callback: CallbackQuery, db_user: dict = None, bot: Bot = None):
    """Уведомление администратора об оплате."""
    user_id = callback.from_user.id
    
    # Отправляем уведомление всем админам
    sent_count = 0
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 Пользователь сообщил об оплате!\n\n"
                f"🆔 ID: {user_id}\n"
                f"👤 Username: @{callback.from_user.username or 'нет'}\n"
                f"📛 Имя: {db_user.get('full_name', 'не указано') if db_user else 'не указано'}\n"
                f"💰 Баланс: {format_balance(db_user.get('balance', 0)) if db_user else 0} ₽\n\n"
                f"Проверьте платеж и пополните баланс."
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    
    if sent_count > 0:
        await callback.answer(
            "✅ Уведомление отправлено администратору.\n"
            "Баланс будет пополнен в течение часа.",
            show_alert=True
        )
    else:
        await callback.answer(
            "⚠️ Не удалось отправить уведомление.\n"
            "Пожалуйста, напишите администратору вручную.",
            show_alert=True
        )


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

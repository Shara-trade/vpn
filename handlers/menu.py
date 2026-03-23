"""
Обработчики главного меню пользователя.
"""

from loguru import logger
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import get_main_keyboard
from database import queries
from handlers.start import show_main_menu
from handlers.profile import show_profile
from handlers.key import show_key
from utils.constants import SUPPORT_MESSAGE, BOT_NAME
from keyboards import get_support_keyboard

router = Router()


@router.message(F.text == "🔌 Мой ключ")
async def menu_my_key(message: Message, db_user: dict = None):
    """Переход в раздел 'Мой ключ'."""
    logger.warning(f"[HANDLER] menu_my_key выполнен для user={message.from_user.id}, status={db_user.get('status') if db_user else 'None'}")
    from handlers.key import show_key
    await show_key(message, db_user)


@router.message(F.text == "📊 Профиль")
async def menu_profile(message: Message, db_user: dict = None):
    """Переход в раздел 'Профиль'."""
    await show_profile(message, db_user)


@router.message(F.text == "💰 Купить / Продлить")
async def menu_purchase(message: Message, db_user: dict = None):
    """Переход в раздел покупки тарифа."""
    from handlers.purchase import show_tariffs
    await show_tariffs(message, db_user)


@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message):
    """Переход в раздел поддержки."""
    await message.answer(
        SUPPORT_MESSAGE.format(bot_name=BOT_NAME),
        reply_markup=get_support_keyboard()
    )


@router.message(F.text == "❌ Отмена")
async def menu_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия и возврат в главное меню."""
    await state.clear()
    
    db_user = await queries.get_user(message.from_user.id)
    await show_main_menu(message, db_user)

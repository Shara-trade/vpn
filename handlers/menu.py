"""
Обработчики главного меню пользователя (StarinaVPN).
Reply-кнопки без эмодзи.
"""

from loguru import logger
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import (
    get_main_keyboard, get_support_keyboard, get_reviews_keyboard,
    get_servers_status_keyboard, get_promocode_start_keyboard, get_buy_keyboard,
    get_keys_empty_keyboard
)
from database import queries
from handlers.start import show_main_menu
from handlers.profile import show_profile
from handlers.keys import show_keys
from utils.constants import (
    SUPPORT_MESSAGE, BOT_NAME, TARIFFS_MESSAGE, REVIEWS_MESSAGE,
    PROMOCODE_ENTER_MESSAGE, SERVERS_STATUS_MESSAGE
)
from utils.helpers import get_user_balance_rub

router = Router()


@router.message(F.text == "Купить")
async def menu_buy(message: Message, db_user: dict = None):
    """Переход в раздел 'Купить'."""
    from handlers.purchase import show_buy_menu
    await show_buy_menu(message, db_user)


@router.message(F.text == "Мои ключи")
async def menu_my_keys(message: Message, db_user: dict = None):
    """Переход в раздел 'Мои ключи'."""
    await show_keys(message, db_user)


@router.message(F.text == "Профиль")
async def menu_profile(message: Message, db_user: dict = None):
    """Переход в раздел 'Профиль'."""
    await show_profile(message, db_user)


@router.message(F.text == "Поддержка")
async def menu_support(message: Message):
    """Переход в раздел 'Поддержка'."""
    await message.answer(
        SUPPORT_MESSAGE,
        reply_markup=get_support_keyboard()
    )


@router.message(F.text == "Отзывы")
async def menu_reviews(message: Message):
    """Переход в раздел 'Отзывы'."""
    await message.answer(
        REVIEWS_MESSAGE,
        reply_markup=get_reviews_keyboard()
    )


@router.message(F.text == "Промокод")
async def menu_promocode(message: Message, state: FSMContext):
    """Переход в раздел 'Промокод'."""
    from aiogram.fsm.state import State, StatesGroup
    
    class PromoStates(StatesGroup):
        enter_code = State()
    
    await state.set_state(PromoStates.enter_code)
    await message.answer(
        PROMOCODE_ENTER_MESSAGE,
        reply_markup=get_promocode_start_keyboard()
    )


@router.message(F.text == "Статус серверов")
async def menu_servers_status(message: Message):
    """Переход в раздел 'Статус серверов'."""
    from database.queries import get_active_servers
    
    servers = await get_active_servers()
    
    if not servers:
        await message.answer("⚠️ Нет доступных серверов")
        return
    
    await message.answer(
        SERVERS_STATUS_MESSAGE.format(servers_list=""),
        reply_markup=get_servers_status_keyboard(servers)
    )


@router.message(F.text == "❌ Отмена")
async def menu_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия и возврат в главное меню."""
    await state.clear()
    
    db_user = await queries.get_user(message.from_user.id)
    await show_main_menu(message, db_user)

"""
Хендлер главного меню.
"""
from aiogram import Router, F
from aiogram.types import Message

from database.models import User
from keyboards.reply import get_main_keyboard
from utils.constants import BTN_MY_KEY, BTN_PROFILE, BTN_BUY, BTN_SUPPORT

router = Router()


@router.message(F.text == BTN_MY_KEY)
async def menu_my_key(message: Message, user: User):
    """Раздел 'Мой ключ'."""
    # Перенаправляем в хендлер key.py
    from handlers.key import show_key
    await show_key(message, user)


@router.message(F.text == BTN_PROFILE)
async def menu_profile(message: Message, user: User):
    """Раздел 'Профиль'."""
    # Перенаправляем в хендлер profile.py
    from handlers.profile import show_profile
    await show_profile(message, user)


@router.message(F.text == BTN_BUY)
async def menu_buy(message: Message, user: User):
    """Раздел 'Купить / Продлить'."""
    # Перенаправляем в хендлер purchase.py
    from handlers.purchase import show_tariffs
    await show_tariffs(message, user)


@router.message(F.text == BTN_SUPPORT)
async def menu_support(message: Message, user: User):
    """Раздел 'Поддержка'."""
    # Перенаправляем в хендлер support.py
    from handlers.support import show_support
    await show_support(message, user)

"""
Хендлер команды /start.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import BOT_NAME
from database.models import User
from database.queries import get_user_by_referral_code
from keyboards.reply import get_main_keyboard
from keyboards.inline import get_start_keyboard, get_referral_activate_keyboard
from utils.constants import START_WELCOME, START_WELCOME_BACK, REFERRAL_INVITE
from utils.helpers import format_datetime, get_status_text

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User):
    """Обработка команды /start."""
    # Проверяем реферальный параметр
    args = message.text.split()
    referral_code = None
    
    if len(args) > 1 and args[1].startswith("ref"):
        referral_code = args[1]
    
    # Если есть реферальный код и это не текущий пользователь
    if referral_code:
        referrer = await get_user_by_referral_code(referral_code)
        
        if referrer and referrer.user_id != user.user_id and not user.referred_by:
            # Показываем приглашение с бонусом
            await message.answer(
                REFERRAL_INVITE.format(
                    bot_name=BOT_NAME,
                    bonus_days=4,
                    default_days=3,
                    bonus_amount=50
                ),
                reply_markup=get_referral_activate_keyboard(referral_code)
            )
            return
    
    # Если у пользователя уже есть активная подписка
    if user.expires_at and user.status not in ["trial", "blocked"]:
        status = get_status_text(user.expires_at, user.status)
        
        await message.answer(
            START_WELCOME_BACK.format(
                status=status,
                tariff="Премиум" if user.status == "active" else "Не активен",
                expires=format_datetime(user.expires_at) if user.expires_at else "Не указано",
                server="Не выбран"
            ),
            reply_markup=get_main_keyboard()
        )
    else:
        # Новый пользователь
        is_new = not user.trial_used
        
        await message.answer(
            START_WELCOME,
            reply_markup=get_start_keyboard(is_new_user=is_new)
        )


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, user: User):
    """Возврат в главное меню."""
    status = get_status_text(user.expires_at, user.status)
    
    text = f"""🦎 {BOT_NAME} | Главный экран

Статус: {status}
Тариф: {"Премиум" if user.status == "active" else "Не активен"}
Действует до: {format_datetime(user.expires_at) if user.expires_at else "Не указано"}
Сервер: Не выбран

Выбери действие:"""
    
    await callback.message.edit_text(
        text,
        reply_markup=None
    )
    await callback.message.answer(
        text,
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

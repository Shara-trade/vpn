"""
Хендлер профиля.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import BOT_NAME, PAYMENT_CONTACT
from database.models import User
from database.queries import get_user_transactions, get_user_referrals, get_server_by_id
from keyboards.reply import get_main_keyboard
from keyboards.inline import get_profile_keyboard, get_back_keyboard
from utils.constants import PROFILE_INFO, BALANCE_HISTORY
from utils.helpers import format_datetime, format_balance, format_bytes

router = Router()


async def show_profile(message: Message, user: User):
    """Показывает профиль пользователя."""
    # Получаем сервер
    server_name = "Не выбран"
    if user.server_id:
        server = await get_server_by_id(user.server_id)
        if server:
            server_name = server.display_name
    
    # Получаем рефералов
    referrals = await get_user_referrals(user.user_id)
    
    # Формируем реферальную ссылку
    bot_username = message.bot.username
    referral_link = f"https://t.me/{bot_username}?start={user.referral_code}"
    
    # Трафик
    traffic = format_bytes(user.total_traffic) if user.total_traffic else "0 B"
    
    # Статус
    from utils.helpers import get_status_text
    status = get_status_text(user.expires_at, user.status)
    
    text = PROFILE_INFO.format(
        user_id=user.user_id,
        registered_at=format_datetime(user.registered_at),
        status=status,
        server=server_name,
        balance=format_balance(user.balance),
        traffic=traffic,
        referrals_count=len(referrals),
        referral_earnings=format_balance(user.referral_earnings),
        referral_link=referral_link,
        payment_contact=PAYMENT_CONTACT
    )
    
    await message.answer(
        text,
        reply_markup=get_profile_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "go_to_profile")
async def cb_go_to_profile(callback: CallbackQuery, user: User):
    """Переход в профиль по callback."""
    await show_profile(callback.message, user)
    await callback.answer()


@router.callback_query(F.data == "show_profile")
async def cb_show_profile(callback: CallbackQuery, user: User):
    """Показать профиль по callback."""
    await show_profile(callback.message, user)
    await callback.answer()


@router.callback_query(F.data == "balance_history")
async def cb_balance_history(callback: CallbackQuery, user: User):
    """История операций."""
    transactions = await get_user_transactions(user.user_id, limit=10)
    
    history_lines = []
    for tx in transactions:
        date_str = format_datetime(tx.created_at, "%d.%m.%Y %H:%M")
        
        if tx.amount >= 0:
            amount_str = f"+{format_balance(tx.amount)}"
        else:
            amount_str = f"-{format_balance(abs(tx.amount))}"
        
        type_names = {
            "payment": "Пополнение",
            "purchase": "Покупка",
            "referral": "Реферальный бонус",
            "admin": "Начисление от админа"
        }
        
        type_name = type_names.get(tx.type, tx.type)
        desc = f" ({tx.description})" if tx.description else ""
        
        history_lines.append(f"🗓 {date_str} — {type_name}: {amount_str} ₽{desc}")
    
    if not history_lines:
        history_lines.append("История пуста")
    
    text = BALANCE_HISTORY.format(
        history="\n".join(history_lines),
        balance=format_balance(user.balance)
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("go_to_profile")
    )
    await callback.answer()

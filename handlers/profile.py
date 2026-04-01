"""
Обработчики раздела 'Профиль'.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import queries
from keyboards import (
    get_profile_keyboard,
    get_back_to_profile_keyboard,
    get_main_keyboard,
    get_back_and_close_keyboard,
)
from utils.constants import (
    PROFILE_MESSAGE,
    BALANCE_HISTORY_HEADER,
    BALANCE_HISTORY_ITEM,
    BALANCE_CURRENT,
    BOT_NAME,
)
from utils.helpers import (
    format_balance,
    format_date,
    format_datetime,
    get_status_text,
    format_traffic,
)

router = Router()


class PromoState(StatesGroup):
    """Состояния для промокода."""
    waiting_promo = State()


async def show_profile(message: Message, db_user: dict = None):
    """
    Показ профиля пользователя.
    """
    user_id = db_user["user_id"]
    
    # Получаем сервер
    server_name = "Не выбран"
    if db_user.get("server_id"):
        server = await queries.get_server(db_user["server_id"])
        if server:
            server_name = server["name"]
    
    # Получаем статистику рефералов
    ref_stats = await queries.get_referral_stats(user_id)
    
    # Формируем реферальную ссылку
    referral_link = f"https://t.me/{(await message.bot.get_me()).username}?start={db_user['referral_code']}"
    
    # Определяем статус
    status = get_status_text(
        db_user.get("status", "active"),
        db_user.get("expires_at")
    )
    
    # Форматируем даты
    registered_at = format_date(db_user["registered_at"]) if db_user.get("registered_at") else "Неизвестно"
    expires_at = "Не активна"
    if db_user.get("expires_at"):
        from datetime import datetime
        expires_str = format_date(db_user["expires_at"])
        expires_at = f"{status} до {expires_str}"
    
    # Трафик
    traffic = format_traffic(db_user.get("traffic_used", 0))
    
    # Отправляем профиль
    await message.answer(
        PROFILE_MESSAGE.format(
            user_id=user_id,
            registered_at=registered_at,
            status=expires_at,
            server=server_name,
            balance=format_balance(db_user.get("balance", 0)),
            traffic=traffic,
            referrals_count=ref_stats["referrals_count"],
            referral_earnings=format_balance(ref_stats["referral_earnings"]),
            referral_link=referral_link,
        ),
        reply_markup=get_profile_keyboard(referral_link)
    )


# ================== CALLBACK HANDLERS ==================

@router.callback_query(F.data == "go_to_profile")
async def callback_go_to_profile(callback: CallbackQuery, db_user: dict = None):
    """Переход в профиль из inline-кнопки."""
    user_id = callback.from_user.id
    
    # Получаем актуальные данные пользователя
    db_user = await queries.get_user(user_id)
    
    # Удаляем предыдущее сообщение
    await callback.message.delete()
    
    # Показываем профиль
    await show_profile(callback.message, db_user)
    
    await callback.answer()


@router.callback_query(F.data == "show_profile")
async def callback_show_profile(callback: CallbackQuery, db_user: dict = None):
    """Показ профиля из inline-кнопки."""
    await callback_go_to_profile(callback, db_user)


@router.callback_query(F.data == "balance_history")
async def callback_balance_history(callback: CallbackQuery, db_user: dict = None):
    """Показ истории операций."""
    user_id = callback.from_user.id
    
    # Получаем транзакции
    transactions = await queries.get_user_transactions(user_id, limit=10)
    
    if not transactions:
        await callback.answer(
            "📊 История операций пуста",
            show_alert=True
        )
        return
    
    # Формируем сообщение
    history_text = BALANCE_HISTORY_HEADER
    
    type_names = {
        "payment": "Пополнение",
        "purchase": "Покупка",
        "referral": "Реферальный бонус",
        "admin": "Начисление от админа",
        "trial": "Пробный период",
    }
    
    for tx in transactions:
        amount = tx["amount"] / 100
        sign = "+" if tx["amount"] >= 0 else ""
        tx_type = type_names.get(tx["type"], tx["type"])
        
        history_text += BALANCE_HISTORY_ITEM.format(
            date=format_datetime(tx["created_at"]),
            type=tx_type,
            amount=f"{sign}{amount:.0f}",
            balance=format_balance(tx.get("balance_after", 0))
        ) + "\n"
    
    history_text += BALANCE_CURRENT.format(
        balance=format_balance(db_user.get("balance", 0))
    )
    
    await callback.message.edit_text(
        history_text,
        reply_markup=get_back_to_profile_keyboard()
    )
    
    await callback.answer()


@router.callback_query(F.data == "enter_promo")
async def callback_enter_promo(callback: CallbackQuery, state: FSMContext):
    """Ввод промокода."""
    await callback.message.edit_text(
        "🎁 Введи промокод для активации:",
        reply_markup=get_back_and_close_keyboard("go_to_profile")
    )
    
    await state.set_state(PromoState.waiting_promo)
    await callback.answer()


@router.message(PromoState.waiting_promo)
async def process_promo_code(message: Message, state: FSMContext, db_user: dict = None):
    """Обработка введенного промокода."""
    user_id = message.from_user.id
    promo_code = message.text.strip().upper()
    
    # Проверяем промокод
    success, msg, promocode = await queries.activate_promocode(user_id, promo_code)
    
    if not success:
        await message.answer(
            f"{msg}\n\n"
            f"Попробуй другой промокод или обратись в поддержку.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    # Применяем промокод
    await queries.apply_promocode(user_id, promocode)
    
    # Формируем сообщение об успехе
    type_names = {
        "balance": f"💰 Начислено {format_balance(promocode['value'])} ₽ на баланс!",
        "free_days": f"🎁 Добавлено {promocode['value']} дней бесплатного доступа!",
        "subscription_extension": f"📅 Подписка продлена на {promocode['value']} дней!",
        "discount_percent": f"🏷️ Скидка {promocode['value']}% на следующую покупку!",
        "discount_fixed": f"🏷️ Скидка {format_balance(promocode['value'])} ₽ на следующую покупку!"
    }
    
    await message.answer(
        f"✅ Промокод активирован!\n\n"
        f"{type_names.get(promocode['type'], 'Промокод применен')}\n\n"
        f"Проверь свой баланс и подписку в профиле.",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()

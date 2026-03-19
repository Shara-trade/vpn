"""
Хендлер покупки тарифов.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from config import BOT_NAME
from database.models import User
from database.queries import get_tariffs, get_tariff_by_months, update_user, create_transaction
from keyboards.inline import (
    get_tariffs_keyboard, get_purchase_confirm_keyboard,
    get_purchase_success_keyboard, get_balance_error_keyboard
)
from utils.constants import TARIFFS_LIST, PURCHASE_CONFIRM, PURCHASE_SUCCESS, PURCHASE_ERROR
from utils.helpers import format_balance, format_datetime, get_tariff_name

router = Router()


async def show_tariffs(message: Message, user: User):
    """Показывает доступные тарифы."""
    tariffs = await get_tariffs()
    
    if not tariffs:
        await message.answer("❌ Тарифы не найдены. Обратитесь в поддержку.")
        return
    
    # Формируем список тарифов
    prices = {}
    for t in tariffs:
        prices[t.months] = t.price
    
    text = TARIFFS_LIST.format(
        bot_name=BOT_NAME,
        price_1=format_balance(prices.get(1, 29900)),
        price_3=format_balance(prices.get(3, 79900)),
        price_6=format_balance(prices.get(6, 149900)),
        price_12=format_balance(prices.get(12, 249900)),
        balance=format_balance(user.balance)
    )
    
    await message.answer(
        text,
        reply_markup=get_tariffs_keyboard(tariffs, user.balance)
    )


@router.callback_query(F.data.startswith("buy_tariff_"))
async def cb_buy_tariff(callback: CallbackQuery, user: User, state: FSMContext):
    """Выбор тарифа для покупки."""
    months = int(callback.data.split("_")[-1])
    
    tariff = await get_tariff_by_months(months)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Проверяем баланс
    if user.balance < tariff.price:
        text = PURCHASE_ERROR.format(
            tariff_name=tariff.name,
            tariff_price=format_balance(tariff.price),
            balance=format_balance(user.balance),
            missing=format_balance(tariff.price - user.balance)
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_balance_error_keyboard()
        )
        await callback.answer()
        return
    
    # Показываем подтверждение
    new_balance = user.balance - tariff.price
    
    text = PURCHASE_CONFIRM.format(
        tariff_name=tariff.name,
        tariff_price=format_balance(tariff.price),
        balance=format_balance(user.balance),
        new_balance=format_balance(new_balance)
    )
    
    # Сохраняем выбранный тариф в state
    await state.update_data(selected_tariff_months=months)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_purchase_confirm_keyboard(months)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_purchase_"))
async def cb_confirm_purchase(callback: CallbackQuery, user: User, state: FSMContext):
    """Подтверждение покупки."""
    months = int(callback.data.split("_")[-1])
    
    tariff = await get_tariff_by_months(months)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Проверяем баланс ещё раз
    if user.balance < tariff.price:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return
    
    # Списываем средства
    new_balance = user.balance - tariff.price
    
    # Вычисляем новую дату истечения
    now = datetime.now()
    if user.expires_at and user.expires_at > now:
        expires_at = user.expires_at + timedelta(days=30 * months)
    else:
        expires_at = now + timedelta(days=30 * months)
    
    # Обновляем пользователя
    await update_user(
        user.user_id,
        balance=new_balance,
        expires_at=expires_at,
        status="active"
    )
    
    # Создаём транзакцию
    await create_transaction(
        user_id=user.user_id,
        amount=-tariff.price,
        transaction_type="purchase",
        description=f"Покупка тарифа: {tariff.name}"
    )
    
    # Здесь должна быть генерация ключа через X-UI API
    # Пока используем заглушку
    key = f"vless://test-uuid@example.com:443?security=tls&type=tcp#FreakVPN_TEST"
    
    text = PURCHASE_SUCCESS.format(
        amount=format_balance(tariff.price),
        balance=format_balance(new_balance),
        expires=format_datetime(expires_at),
        key=key
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_purchase_success_keyboard()
    )
    await callback.answer("✅ Покупка успешна!")
    
    # Очищаем state
    await state.clear()


@router.callback_query(F.data == "cancel_purchase")
async def cb_cancel_purchase(callback: CallbackQuery, user: User, state: FSMContext):
    """Отмена покупки."""
    await state.clear()
    await show_tariffs(callback.message, user)
    await callback.answer("❌ Покупка отменена")

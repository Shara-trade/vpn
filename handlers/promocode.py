from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from database import queries
from utils.constants import PROMOCODE_SUCCESS_MESSAGE, PROMOCODE_ERROR_MESSAGE
from keyboards import get_main_keyboard

router = Router()

class PromocodeState(StatesGroup):
    entering_code = State()

@router.message(PromocodeState.entering_code)
async def process_promocode(message: Message, state: FSMContext, db_user: dict = None):
    user_id = message.from_user.id
    code = message.text.strip().upper()
    promocode = await queries.get_promocode(code)
    
    if not promocode:
        await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Промокод не найден"), reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    if not promocode.get("is_active"):
        await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Промокод неактивен"), reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    if promocode.get("expires_at"):
        from datetime import datetime
        if datetime.utcnow() > promocode["expires_at"]:
            await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Промокод истек"), reply_markup=get_main_keyboard())
            await state.clear()
            return
    
    max_uses = promocode.get("max_uses", 0)
    used_count = promocode.get("used_count", 0)
    if max_uses > 0 and used_count >= max_uses:
        await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Лимит использований исчерпан"), reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    usage = await queries.get_promocode_usage(promocode["id"], user_id)
    if usage:
        await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Вы уже использовали этот промокод"), reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    promocode_type = promocode.get("type")
    value = promocode.get("value")
    
    try:
        if promocode_type == "discount_percent":
            await message.answer(PROMOCODE_SUCCESS_MESSAGE.format(reward_description=f"Скидка {value}% на следующую покупку!"), reply_markup=get_main_keyboard())
        elif promocode_type == "discount_fixed":
            discount_rub = value / 100
            await message.answer(PROMOCODE_SUCCESS_MESSAGE.format(reward_description=f"Скидка {discount_rub} ₽ на следующую покупку!"), reply_markup=get_main_keyboard())
        elif promocode_type == "free_days":
            days = value
            from datetime import datetime, timedelta
            keys = await queries.get_user_keys(user_id, active_only=True)
            for key in keys:
                expires_at = key["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                new_expires = expires_at + timedelta(days=days)
                await queries.update_key_expires(key["id"], new_expires)
            await message.answer(PROMOCODE_SUCCESS_MESSAGE.format(reward_description=f"+{days} дней ко всем вашим ключам!"), reply_markup=get_main_keyboard())
        elif promocode_type == "balance":
            balance_rub = value / 100
            new_balance = await queries.update_user_balance(user_id, value)
            await queries.create_transaction(user_id=user_id, amount=value, transaction_type="promocode", description=f"Промокод: {code}")
            await message.answer(PROMOCODE_SUCCESS_MESSAGE.format(reward_description=f"+{balance_rub} ₽ на баланс!"), reply_markup=get_main_keyboard())
        elif promocode_type == "subscription_extension":
            days = value
            from datetime import datetime, timedelta
            keys = await queries.get_user_keys(user_id, active_only=True)
            for key in keys:
                expires_at = key["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                new_expires = expires_at + timedelta(days=days)
                await queries.update_key_expires(key["id"], new_expires)
            await message.answer(PROMOCODE_SUCCESS_MESSAGE.format(reward_description=f"+{days} дней ко всем вашим ключам!"), reply_markup=get_main_keyboard())
        else:
            await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Неизвестный тип промокода"), reply_markup=get_main_keyboard())
            await state.clear()
            return
        
        await queries.increment_promocode_usage(promocode["id"])
        await queries.create_promocode_usage(promocode["id"], user_id)
        await queries.add_log(category="promocode", action="promocode_activated", user_id=user_id, details={"code": code, "type": promocode_type, "value": value})
        logger.info(f"Промокод активирован: user_id={user_id}, code={code}, type={promocode_type}")
        
    except Exception as e:
        logger.error(f"Ошибка при активации промокода: {e}")
        await message.answer(PROMOCODE_ERROR_MESSAGE.format(error="Произошла ошибка"), reply_markup=get_main_keyboard())
    
    await state.clear()

__all__ = ["process_promocode", "PromocodeState"]

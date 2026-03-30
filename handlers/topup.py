from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from config import config
from database import queries
from keyboards import get_topup_menu_keyboard, get_topup_confirm_keyboard, get_main_keyboard, get_admin_topup_keyboard
from utils.constants import TOPUP_MENU_MESSAGE, TOPUP_ENTER_AMOUNT_MESSAGE, TOPUP_PAYMENT_DETAILS_MESSAGE, TOPUP_PENDING_MESSAGE, TOPUP_ADMIN_NOTIFICATION
from utils.helpers import format_balance

router = Router()

class TopupStates(StatesGroup):
    enter_amount = State()

@router.callback_query(F.data == "start_topup")
async def callback_start_topup(callback: CallbackQuery):
    await callback.message.edit_text(TOPUP_MENU_MESSAGE, reply_markup=get_topup_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "start_topup_input")
async def callback_start_topup_input(callback: CallbackQuery, state: FSMContext):
    min_topup = await queries.get_min_topup()
    await callback.message.edit_text(TOPUP_ENTER_AMOUNT_MESSAGE.format(min_amount=min_topup), reply_markup=None)
    await state.set_state(TopupStates.enter_amount)
    await callback.answer()

@router.message(TopupStates.enter_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверная сумма. Введите число больше 0:")
        return
    
    min_topup = await queries.get_min_topup()
    if amount < min_topup:
        await message.answer(f"❌ Минимальная сумма пополнения: {min_topup} ₽")
        return
    
    payment_details = await queries.get_setting("payment_details") or "Перевод на карту: +7XXX XXX-XX-XX"
    
    await message.answer(TOPUP_PAYMENT_DETAILS_MESSAGE.format(amount=amount, payment_details=payment_details), reply_markup=get_topup_confirm_keyboard(amount))
    await state.clear()

@router.callback_query(F.data.startswith("topup_paid_"))
async def callback_topup_paid(callback: CallbackQuery, db_user: dict = None, bot: Bot = None):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    
    await queries.add_log(category="payment", action="topup_request", user_id=user_id, amount=amount * 100, details={"status": "pending"})
    
    await callback.message.edit_text(TOPUP_PENDING_MESSAGE, reply_markup=get_main_keyboard())
    
    user_info = f"@{callback.from_user.username}" if callback.from_user.username else f"ID: {user_id}"
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, TOPUP_ADMIN_NOTIFICATION.format(user_info=user_info, amount=amount), reply_markup=get_admin_topup_keyboard(user_id, amount))
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    
    await callback.answer("✅ Заявка отправлена!")
    logger.info(f"Заявка на пополнение: user_id={user_id}, amount={amount}")

@router.callback_query(F.data.startswith("admin_add_balance_"))
async def callback_admin_approve_topup(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    user_id = int(parts[3])
    amount = int(parts[4])
    
    new_balance = await queries.update_user_balance(user_id, amount * 100)
    
    await queries.create_transaction(user_id=user_id, amount=amount * 100, transaction_type="payment", description="Пополнение баланса через бота", admin_id=callback.from_user.id)
    
    try:
        await bot.send_message(user_id, f"✅ Баланс пополнен!\n\nСумма: +{amount} ₽\nТекущий баланс: {format_balance(new_balance)} ₽")
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    await callback.message.edit_text(f"✅ Баланс пополнен!\n\nПользователь: {user_id}\nСумма: {amount} ₽\nНовый баланс: {format_balance(new_balance)} ₽")
    
    await callback.answer("✅ Баланс пополнен")
    logger.info(f"Админ пополнил баланс: user_id={user_id}, amount={amount}")

@router.callback_query(F.data.startswith("admin_reject_payment_"))
async def callback_admin_reject_topup(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    user_id = int(parts[3])
    amount = int(parts[4])
    
    try:
        await bot.send_message(user_id, "❌ Заявка на пополнение отклонена.\n\nПожалуйста, свяжитесь с поддержкой: @StarinaVPN_Support_bot")
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    await callback.message.edit_text(f"❌ Заявка отклонена.\n\nПользователь: {user_id}\nСумма: {amount} ₽")
    
    await callback.answer("Заявка отклонена")
    logger.info(f"Админ отклонил заявку: user_id={user_id}, amount={amount}")

"""
Обработчики покупки и продления тарифов.
Поддержка множественных ключей (до 5) и балансировки нагрузки.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from loguru import logger

from database import queries
from keyboards import (
    get_buy_keyboard,
    get_purchase_confirm_keyboard,
    get_purchase_success_keyboard,
    get_purchase_error_keyboard,
    get_main_keyboard,
    get_subscription_check_keyboard,
    get_keys_keyboard,
)
from utils.constants import (
    BUY_MENU_MESSAGE,
    PURCHASE_CONFIRM_MESSAGE,
    PURCHASE_SUCCESS_MESSAGE,
    PURCHASE_ERROR_MESSAGE,
    KEYS_LIMIT_REACHED_MESSAGE,
    BOT_NAME,
)
from utils.helpers import format_balance, format_date, parse_datetime
from services.xui_api import XuiService, XuiError
from handlers.start import check_channel_subscription

router = Router()


async def show_buy_menu(message: Message, db_user: dict = None, extend_key_id: int = None):
    """
    Показ меню покупки с тарифами и пробным периодом.
    
    Args:
        message: Сообщение от пользователя
        db_user: Данные пользователя из БД
        extend_key_id: ID ключа для продления (если продление)
    """
    user_id = db_user["user_id"]
    
    # Получаем тарифы из БД
    tariffs = await queries.get_tariffs()
    
    if not tariffs:
        await message.answer(
            "❌ В данный момент нет доступных тарифов.\n"
            "Обратитесь в поддержку: @ShadowRing"
        )
        return
    
    # Получаем баланс и количество ключей
    balance = db_user.get("balance", 0)
    keys_count = len(await queries.get_user_keys(user_id, active_only=True))
    
    # Проверяем, использовал ли пробный период
    has_trial = await queries.has_used_trial(user_id)
    
    await message.answer(
        BUY_MENU_MESSAGE.format(
            balance=format_balance(balance),
            keys_count=keys_count
        ),
        reply_markup=get_buy_keyboard(tariffs, has_trial=has_trial, extend_key_id=extend_key_id)
    )
    

# ================== CALLBACK HANDLERS ==================

# ================== CALLBACK HANDLERS ==================

# Handlers для покупки тарифов по ТЗ
@router.callback_query(F.data == "buy_trial")
async def callback_buy_trial(callback: CallbackQuery, db_user: dict = None):
    """Покупка пробного ключа."""
    user_id = callback.from_user.id
    
    # Проверяем подписку на канал
    is_subscribed = await check_channel_subscription(callback.bot, user_id)
    if not is_subscribed:
        await callback.message.edit_text(
            "<b>Для покупки ключа необходимо подписаться на новостной канал.</b>",
            reply_markup=get_subscription_check_keyboard("buy_trial")
        )
        await callback.answer()
        return
        
    # Проверяем лимит ключей (макс 5)
    keys_count = len(await queries.get_user_keys(user_id, active_only=True))
    if keys_count >= 5:
        await callback.answer(
            "❌ У вас уже 5 активных ключей. Удалите неиспользуемые ключи.",
            show_alert=True
        )
        return
    
    # Проверяем, использовал ли пробный период
    if db_user.get("trial_used"):
        await callback.answer("❌ Вы уже использовали пробный период", show_alert=True)
        return
    
    # Перенаправляем на создание пробного ключа
    from handlers.start import callback_trial_get
    await callback_trial_get(callback, db_user)


@router.callback_query(F.data == "buy_7days")
async def callback_buy_7days(callback: CallbackQuery, db_user: dict = None):
    """Покупка тарифа на 7 дней."""
    tariff = await queries.get_tariff_by_days(7)
    if not tariff:
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    await _process_buy_tariff(callback, db_user, tariff)
    

@router.callback_query(F.data == "buy_1month")
async def callback_buy_1month(callback: CallbackQuery, db_user: dict = None):
    """Покупка тарифа на 1 месяц."""
    tariff = await queries.get_tariff_by_days(30)
    if not tariff:
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    await _process_buy_tariff(callback, db_user, tariff)
    

@router.callback_query(F.data == "buy_3months")
async def callback_buy_3months(callback: CallbackQuery, db_user: dict = None):
    """Покупка тарифа на 3 месяца."""
    tariff = await queries.get_tariff_by_days(90)
    if not tariff:
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    await _process_buy_tariff(callback, db_user, tariff)


@router.callback_query(F.data == "buy_6months")
async def callback_buy_6months(callback: CallbackQuery, db_user: dict = None):
    """Покупка тарифа на 6 месяцев."""
    tariff = await queries.get_tariff_by_days(180)
    if not tariff:
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    await _process_buy_tariff(callback, db_user, tariff)


@router.callback_query(F.data == "buy_12months")
async def callback_buy_12months(callback: CallbackQuery, db_user: dict = None):
    """Покупка тарифа на 12 месяцев."""
    tariff = await queries.get_tariff_by_days(360)
    if not tariff:
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    await _process_buy_tariff(callback, db_user, tariff)


async def _process_buy_tariff(callback: CallbackQuery, db_user: dict, tariff: dict):
    """Общая логика покупки тарифа."""
    user_id = callback.from_user.id
    
    # Проверяем подписку на канал
    is_subscribed = await check_channel_subscription(callback.bot, user_id)
    if not is_subscribed:
        await callback.message.edit_text(
            "<b>Для покупки ключа необходимо подписаться на новостной канал.</b>",
            reply_markup=get_subscription_check_keyboard(f"buy_tariff_{tariff['id']}")
        )
        await callback.answer()
        return

    # Проверяем лимит ключей (макс 5)
    keys_count = len(await queries.get_user_keys(user_id, active_only=True))
    if keys_count >= 5:
        await callback.answer(
            "❌ Достигнут лимит в 5 ключей. Удалите неиспользуемые ключи.",
            show_alert=True
        )
        return

    # Проверяем баланс
    balance = db_user.get("balance", 0)
    price = tariff["price"]
    
    if balance < price:
        missing = price - balance
        await callback.message.edit_text(
            PURCHASE_ERROR_MESSAGE.format(
                tariff_name=tariff["name"],
                price=format_balance(price),
                balance=format_balance(balance),
                missing=format_balance(missing)
            ),
            reply_markup=get_purchase_error_keyboard()
        )
        await callback.answer()
        return
    
    # Показываем подтверждение
    new_balance = balance - price
    await callback.message.edit_text(
        PURCHASE_CONFIRM_MESSAGE.format(
            tariff_name=tariff["name"],
            price=format_balance(price),
            balance=format_balance(balance),
            new_balance=format_balance(new_balance)
        ),
        reply_markup=get_purchase_confirm_keyboard(tariff["id"], extend_key_id=None)
    )
    await callback.answer()


# Старый handler для совместимости (если используется tariff_id)
@router.callback_query(F.data.startswith("buy_tariff_"))
async def callback_buy_tariff(callback: CallbackQuery, db_user: dict = None):
    """
    Выбор тарифа для покупки нового ключа.
    Проверяет лимит ключей и подписку на канал.
    """
    user_id = callback.from_user.id
    tariff_id = int(callback.data.split("_")[2])
    
    # Проверяем подписку на канал
    is_subscribed = await check_channel_subscription(callback.bot, user_id)
    if not is_subscribed:
        await callback.message.edit_text(
            "<b>Для покупки ключа необходимо подписаться на новостной канал.</b>",
            reply_markup=get_subscription_check_keyboard(f"buy_tariff_{tariff_id}")
        )
        await callback.answer()
        return
        
    # Проверяем лимит ключей (макс 5)
    keys_count = len(await queries.get_user_keys(user_id, active_only=True))
    if keys_count >= 5:
        await callback.answer(
            "❌ Достигнут лимит в 5 ключей. Удалите неиспользуемые ключи.",
            show_alert=True
        )
        return
    
    # Получаем тариф
    tariff = await queries.get_tariff(tariff_id)
    if not tariff or not tariff.get("is_active", True):
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    
    # Проверяем баланс
    balance = db_user.get("balance", 0)
    price = tariff["price"]
    
    if balance < price:
        missing = price - balance
        await callback.message.edit_text(
            PURCHASE_ERROR_MESSAGE.format(
                tariff_name=tariff["name"],
                price=format_balance(price),
                balance=format_balance(balance),
                missing=format_balance(missing)
            ),
            reply_markup=get_purchase_error_keyboard()
        )
        await callback.answer()
        return
    
    # Показываем подтверждение
    new_balance = balance - price
    await callback.message.edit_text(
        PURCHASE_CONFIRM_MESSAGE.format(
            tariff_name=tariff["name"],
            price=format_balance(price),
            balance=format_balance(balance),
            new_balance=format_balance(new_balance)
        ),
        reply_markup=get_purchase_confirm_keyboard(tariff_id, extend_key_id=None)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_tariff_"))
async def callback_extend_tariff(callback: CallbackQuery, db_user: dict = None):
    """
    Продление существующего ключа.
    """
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    tariff_id = int(parts[2])
    key_id = int(parts[3]) if len(parts) > 3 else None
    
    if not key_id:
        await callback.answer("❌ Ключ не указан", show_alert=True)
        return
    
    # Проверяем существование ключа
    key_data = await queries.get_user_key(key_id)
    if not key_data or key_data["user_id"] != user_id:
        await callback.answer("❌ Ключ не найден", show_alert=True)
        return
    
    # Получаем тариф
    tariff = await queries.get_tariff(tariff_id)
    if not tariff or not tariff.get("is_active", True):
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    
    # Проверяем баланс
    balance = db_user.get("balance", 0)
    price = tariff["price"]
    
    if balance < price:
        missing = price - balance
        await callback.message.edit_text(
            PURCHASE_ERROR_MESSAGE.format(
                tariff_name=tariff["name"],
                price=format_balance(price),
                balance=format_balance(balance),
                missing=format_balance(missing)
            ),
            reply_markup=get_purchase_error_keyboard()
        )
        await callback.answer()
        return
    
    # Показываем подтверждение
    new_balance = balance - price
    await callback.message.edit_text(
        PURCHASE_CONFIRM_MESSAGE.format(
            tariff_name=tariff["name"],
            price=format_balance(price),
            balance=format_balance(balance),
            new_balance=format_balance(new_balance)
        ),
        reply_markup=get_purchase_confirm_keyboard(tariff_id, extend_key_id=key_id)
    )
    await callback.answer()


# Хранилище для защиты от двойных нажатий
_purchase_processing = {}


@router.callback_query(F.data.startswith("confirm_purchase_"))
async def callback_confirm_purchase(callback: CallbackQuery, db_user: dict = None):
    """
    Подтверждение покупки/продления тарифа.
    Создает новый ключ или продлевает существующий.
    Защита от двойных нажатий.
    """
    user_id = callback.from_user.id
    
    # Проверка на дубликат
    if _purchase_processing.get(user_id):
        await callback.answer("⏳ Идёт обработка, подождите...", show_alert=True)
        return
    
    parts = callback.data.split("_")
    tariff_id = int(parts[2])
    extend_key_id = int(parts[3]) if len(parts) > 3 and parts[3] != "None" else None
    
    # Получаем тариф
    tariff = await queries.get_tariff(tariff_id)
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Проверяем активность тарифа
    if not tariff.get("is_active", True):
        await callback.answer("❌ Тариф недоступен", show_alert=True)
        return
    
    # Получаем актуальные данные
    db_user = await queries.get_user(user_id)
    balance = db_user.get("balance", 0)
    price = tariff["price"]
    
    if balance < price:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return
    
    # Устанавливаем флаг обработки
    _purchase_processing[user_id] = True
    
    try:
        await callback.answer("⏳ Обработка покупки...", show_alert=False)
        
        # ===== 1. СПИСЫВАЕМ СРЕДСТВА =====
        new_balance = await queries.update_user_balance(user_id, -price)
        logger.info(f"Списано {price} копеек с баланса user_id={user_id}")
        
        # ===== 2. ОПРЕДЕЛЯЕМ ДЕЙСТВИЕ =====
        if extend_key_id:
            # ПРОДЛЕНИЕ существующего ключа
            await _extend_existing_key(callback, user_id, extend_key_id, tariff, new_balance)
        else:
            # СОЗДАНИЕ нового ключа
            await _create_new_key(callback, user_id, tariff, new_balance)
            
    except Exception as e:
        logger.error(f"Критическая ошибка при покупке: {e}", exc_info=True)
        try:
            await queries.update_user_balance(user_id, price)
        except Exception as refund_error:
            logger.critical(f"Не удалось вернуть средства: {refund_error}")
        
        await callback.message.edit_text(
            "❌ Произошла ошибка. Средства возвращены на баланс.",
            reply_markup=None
        )
    finally:
        # Снимаем флаг обработки
        _purchase_processing[user_id] = False


async def _create_new_key(callback: CallbackQuery, user_id: int, tariff: dict, new_balance: int):
    """Создание нового ключа."""
    days = tariff.get("days", 30 * tariff["months"])
    
    # Выбираем лучший сервер
    server = await queries.select_best_server()
    if not server:
        await callback.answer("❌ Нет доступных серверов", show_alert=True)
        raise Exception("No available servers")
    
    expires_at = datetime.utcnow() + timedelta(days=days)
    
    # Создаем ключ на сервере
    xui = XuiService(server)
    key_data = await xui.create_client(user_id=user_id, days=days)
    
    if not key_data:
        await queries.update_user_balance(user_id, tariff["price"])
        raise Exception("Не удалось создать ключ")
    
    # Сохраняем в БД
    await queries.increment_server_load(server["id"])
    new_key_id = await queries.create_user_key(
        user_id=user_id,
        key=key_data["key"],
        key_uuid=key_data["uuid"],
        server_id=server["id"],
        expires_at=expires_at,
        auto_renew=False
    )
    
    # Транзакция и лог
    await queries.create_transaction(
        user_id=user_id,
        amount=-tariff["price"],
        transaction_type="purchase",
        description=f"Покупка ключа: {tariff['name']}"
    )
    
    await queries.add_log(
        category="payment",
        action="purchase_key",
        user_id=user_id,
        amount=tariff["price"],
        details={"tariff_id": tariff["id"], "key_id": new_key_id}
    )
    
    # Ответ
    await callback.message.edit_text(
        PURCHASE_SUCCESS_MESSAGE.format(
            price=format_balance(tariff["price"]),
            balance=format_balance(new_balance),
            expires_at=format_date(expires_at),
            key=key_data["key"]
        ),
        reply_markup=get_purchase_success_keyboard()
    )
    
    logger.info(f"Создан новый ключ: user_id={user_id}, key_id={new_key_id}")


async def _extend_existing_key(callback: CallbackQuery, user_id: int, key_id: int, 
                               tariff: dict, new_balance: int):
    """Продление существующего ключа."""
    days = tariff.get("days", 30 * tariff["months"])
    
    key_data = await queries.get_user_key(key_id)
    if not key_data or key_data["user_id"] != user_id:
        await callback.answer("❌ Ключ не найден", show_alert=True)
        raise Exception("Key not found")
    
    # Вычисляем новую дату истечения
    current_expires = key_data["expires_at"]
    if isinstance(current_expires, str):
        current_expires = datetime.fromisoformat(current_expires.replace("Z", "+00:00"))
    
    if current_expires > datetime.utcnow():
        expires_at = current_expires + timedelta(days=days)
    else:
        expires_at = datetime.utcnow() + timedelta(days=days)
    
    # Обновляем срок на сервере
    server = await queries.get_server(key_data["server_id"])
    if server:
        xui = XuiService(server)
        await xui.update_client_expiry(key_data["key_uuid"], days)
    
    # Обновляем в БД
    await queries.update_key_expires(key_id, expires_at)
    
    # Транзакция и лог
    await queries.create_transaction(
        user_id=user_id,
        amount=-tariff["price"],
        transaction_type="extension",
        description=f"Продление ключа: {tariff['name']}"
    )
    
    await queries.add_log(
        category="payment",
        action="extend_key",
        user_id=user_id,
        amount=tariff["price"],
        details={"tariff_id": tariff["id"], "key_id": key_id}
    )
    
    # Ответ
    await callback.message.edit_text(
        f"✅ Ключ успешно продлен!\n\n"
        f"💰 Списано: {format_balance(tariff['price'])} ₽\n"
        f"💳 Баланс: {format_balance(new_balance)} ₽\n"
        f"📅 Новый срок: {format_date(expires_at)}",
        reply_markup=get_keys_keyboard(key_id=key_id, has_prev=False, has_next=False, 
                                       auto_renew=key_data["auto_renew"], server_id=key_data["server_id"])
    )
    
    logger.info(f"Ключ продлен: user_id={user_id}, key_id={key_id}")


@router.callback_query(F.data == "cancel_purchase")
async def callback_cancel_purchase(callback: CallbackQuery, db_user: dict = None):
    """Отмена покупки."""
    await callback.message.delete()
    await show_buy_menu(callback.message, db_user)
    await callback.answer("❌ Покупка отменена")


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, db_user: dict = None):
    """Возврат в главное меню."""
    await callback.message.delete()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message, db_user)
    await callback.answer()


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def show_tariffs(message: Message, db_user: dict = None):
    """Обратная совместимость - делегирует show_buy_menu."""
    await show_buy_menu(message, db_user)


# ================== ЭКСПОРТ ==================

__all__ = [
    "show_buy_menu",
    "callback_buy_tariff",
    "callback_extend_tariff",
    "callback_confirm_purchase",
    "callback_cancel_purchase",
    "callback_back_to_main",
]

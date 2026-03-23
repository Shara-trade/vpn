"""
Обработчики покупки и продления тарифов.
Полная реализация с обработкой ошибок и интеграцией X-UI.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from loguru import logger

from database import queries
from keyboards import (
    get_tariffs_keyboard,
    get_purchase_confirm_keyboard,
    get_purchase_success_keyboard,
    get_purchase_error_keyboard,
    get_main_keyboard,
)
from utils.constants import (
    TARIFFS_MESSAGE,
    PURCHASE_CONFIRM_MESSAGE,
    PURCHASE_SUCCESS_MESSAGE,
    PURCHASE_ERROR_MESSAGE,
    BOT_NAME,
)
from utils.helpers import format_balance, format_date, parse_datetime
from services.xui_api import XuiService, XuiError

router = Router()


async def show_tariffs(message: Message, db_user: dict = None):
    """
    Показ доступных тарифов.
    
    Args:
        message: Сообщение от пользователя
        db_user: Данные пользователя из БД
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
    
    # Получаем баланс пользователя
    balance = db_user.get("balance", 0)
    
    # Формируем сообщение с ценами
    prices = {}
    for i, months in enumerate([1, 3, 6, 12]):
        if i < len(tariffs):
            prices[f"price_{months}"] = tariffs[i]["price"] // 100
        else:
            prices[f"price_{months}"] = 0
    
    await message.answer(
        TARIFFS_MESSAGE.format(
            bot_name=BOT_NAME,
            price_1=prices.get("price_1", 0),
            price_3=prices.get("price_3", 0),
            price_6=prices.get("price_6", 0),
            price_12=prices.get("price_12", 0),
            balance=format_balance(balance)
        ),
        reply_markup=get_tariffs_keyboard(tariffs, balance)
    )


# ================== CALLBACK HANDLERS ==================

@router.callback_query(F.data.startswith("buy_tariff_"))
async def callback_buy_tariff(callback: CallbackQuery, db_user: dict = None):
    """
    Выбор тарифа для покупки.
    Показывает подтверждение или ошибку при недостатке средств.
    """
    user_id = callback.from_user.id
    tariff_id = int(callback.data.split("_")[2])
    
    # Получаем тариф из БД
    tariff = await queries.get_tariff(tariff_id)
    
    if not tariff:
        await callback.answer(
            "❌ Тариф не найден. Попробуйте позже.",
            show_alert=True
        )
        return

    # Проверяем, активен ли тариф
    if not tariff.get("is_active", True):
        await callback.answer(
            "❌ Этот тариф временно недоступен.",
            show_alert=True
        )
        return
    
    # Получаем актуальный баланс
    balance = db_user.get("balance", 0)
    price = tariff["price"]
    
    # Проверяем достаточность средств
    if balance < price:
        # Недостаточно средств - показываем ошибку
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
        
    # Хватает средств - показываем подтверждение
    new_balance = balance - price
    
    # Вычисляем скидку для отображения
    savings = await calculate_savings(tariff["months"], price)
    savings_text = f"\n💰 Экономия: {format_balance(savings)} ₽" if savings > 0 else ""
    
    await callback.message.edit_text(
        PURCHASE_CONFIRM_MESSAGE.format(
            tariff_name=tariff["name"],
            price=format_balance(price),
            balance=format_balance(balance),
            new_balance=format_balance(new_balance)
        ) + savings_text,
        reply_markup=get_purchase_confirm_keyboard(tariff_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_purchase_"))
async def callback_confirm_purchase(callback: CallbackQuery, db_user: dict = None):
    """
    Подтверждение покупки тарифа.
    Списывает средства, создает ключ, продлевает подписку.
    """
    user_id = callback.from_user.id
    tariff_id = int(callback.data.split("_")[2])
    
    # Получаем тариф
    tariff = await queries.get_tariff(tariff_id)
    
    if not tariff:
        await callback.answer(
            "❌ Тариф не найден",
            show_alert=True
        )
        return
    
    # Получаем актуальные данные пользователя
    db_user = await queries.get_user(user_id)
    balance = db_user.get("balance", 0)
    price = tariff["price"]
    
    # Двойная проверка баланса
    if balance < price:
        await callback.answer(
            "❌ Недостаточно средств на балансе. Пополните баланс.",
            show_alert=True
        )
        return
    
    # Проверяем наличие активных серверов
    servers = await queries.get_active_servers()
    if not servers:
        await callback.answer(
            "❌ Нет доступных серверов. Обратитесь в поддержку.",
            show_alert=True
        )
        return
    
    try:
        # Показываем что обрабатываем
        await callback.answer("⏳ Обработка покупки...", show_alert=False)
        
        # ===== 1. СПИСЫВАЕМ СРЕДСТВА =====
        new_balance = await queries.update_user_balance(user_id, -price)
        
        logger.info(f"Списано {price} копеек с баланса user_id={user_id}")
        
        # ===== 2. ВЫЧИСЛЯЕМ ДАТУ ИСТЕЧЕНИЯ =====
        days = 30 * tariff["months"]
        
        expires_dt = parse_datetime(db_user.get("expires_at"))
        if expires_dt and expires_dt > datetime.utcnow():
            # Продлеваем с текущей даты истечения
            expires_at = expires_dt + timedelta(days=days)
        else:
            # Новая подписка с текущего момента
            expires_at = datetime.utcnow() + timedelta(days=days)
        
        # ===== 3. ОПРЕДЕЛЯЕМ СЕРВЕР =====
        server = None
        
        if db_user.get("server_id"):
            # Пытаемся использовать текущий сервер
            server = await queries.get_server(db_user["server_id"])
        
        if not server or not server.get("is_active"):
            # Если сервер не назначен или неактивен - берем первый активный
            server = servers[0]
            await queries.set_user_server(user_id, server["id"])
        
        # ===== 4. РАБОТА С X-UI =====
        key = None
        key_uuid = None
        
        try:
            xui = XuiService(server)
            
            # Удаляем старый ключ если есть
            if db_user.get("key_uuid"):
                try:
                    await xui.delete_client(db_user["key_uuid"])
                    logger.debug(f"Старый ключ удален: {db_user['key_uuid'][:20]}...")
                except Exception as e:
                    logger.warning(f"Не удалось удалить старый ключ: {e}")
            
            # Создаем новый ключ
            key_data = await xui.create_client(
                user_id=user_id,
                days=days,
                traffic_limit_gb=0  # Безлимит
            )
            
            if key_data:
                key = key_data["key"]
                key_uuid = key_data["uuid"]
                
                # Сохраняем ключ в БД
                await queries.set_user_key(user_id, key, key_uuid)
                
                logger.info(f"Создан новый ключ для user_id={user_id}")
            else:
                raise XuiError("Не удалось создать ключ на сервере")
                
        except XuiError as e:
            logger.error(f"Ошибка X-UI при создании ключа: {e}")
            # Продолжаем без ключа - пользователь сможет получить его позже
            
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при работе с X-UI: {e}")
            # Продолжаем без ключа
        
        # ===== 5. УСТАНАВЛИВАЕМ ПОДПИСКУ =====
        await queries.set_user_expires(user_id, expires_at)
        
        # ===== 6. СОЗДАЕМ ТРАНЗАКЦИЮ =====
        await queries.create_transaction(
            user_id=user_id,
            amount=-price,
            transaction_type="purchase",
            description=f"Покупка тарифа: {tariff['name']} ({tariff['months']} мес.)"
        )
        
        # ===== 7. ЛОГИРУЕМ =====
        await queries.add_log(
            category="payment",
            action="purchase_tariff",
            user_id=user_id,
            amount=price,
            details={
                "tariff_id": tariff_id,
                "tariff_name": tariff["name"],
                "months": tariff["months"],
                "server_id": server["id"] if server else None
            }
        )
        
        # ===== 8. ФОРМИРУЕМ ОТВЕТ =====
        if key:
            success_text = PURCHASE_SUCCESS_MESSAGE.format(
                price=format_balance(price),
                balance=format_balance(new_balance),
                expires_at=format_date(expires_at),
                key=key
            )
        else:
            # Если ключ не создался
            success_text = f"""✅ Оплата прошла успешно!

С баланса списано: {format_balance(price)} ₽
Остаток на балансе: {format_balance(new_balance)} ₽
Срок действия продлен до: {format_date(expires_at)}

⚠️ Не удалось автоматически создать ключ.
Напиши в поддержку @ShadowRing для получения ключа."""
        
        await callback.message.edit_text(
            success_text,
            reply_markup=get_purchase_success_keyboard()
        )
        
        await callback.answer(
            "✅ Покупка успешна!",
            show_alert=False
        )

        logger.info(
            f"Покупка тарифа: user_id={user_id}, tariff={tariff['name']}, "
            f"price={price/100:.0f}₽, expires={format_date(expires_at)}"
        )

    except Exception as e:
        logger.error(f"Критическая ошибка при покупке: {e}", exc_info=True)
        
        # ВОЗВРАЩАЕМ СРЕДСТВА при ошибке
        try:
            await queries.update_user_balance(user_id, price)
            logger.info(f"Средства возвращены: user_id={user_id}, amount={price}")
        except Exception as refund_error:
            logger.critical(f"Не удалось вернуть средства: {refund_error}")
        
        await callback.message.edit_text(
            "❌ Произошла ошибка при обработке покупки.\n\n"
            "💰 Средства возвращены на ваш баланс.\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=None
        )
        
        await callback.answer(
            "❌ Ошибка покупки. Средства возвращены.",
            show_alert=True
        )


@router.callback_query(F.data == "cancel_purchase")
async def callback_cancel_purchase(callback: CallbackQuery):
    """
    Отмена покупки.
    Возвращает к списку тарифов.
    """
    user_id = callback.from_user.id
    
    # Получаем актуальные данные
    db_user = await queries.get_user(user_id)
    
    # Удаляем сообщение с подтверждением
    await callback.message.delete()
    
    # Показываем тарифы заново
    await show_tariffs(callback.message, db_user)
    
    await callback.answer("❌ Покупка отменена")


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, db_user: dict = None):
    """
    Возврат в главное меню.
    """
    # Удаляем текущее сообщение
    await callback.message.delete()
    
    # Показываем главное меню
    from handlers.start import show_main_menu
    await show_main_menu(callback.message, db_user)
    
    await callback.answer()


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def calculate_savings(months: int, price: int) -> int:
    """
    Расчет экономии при покупке тарифа.
    
    Args:
        months: Количество месяцев в тарифе
        price: Цена тарифа в копейках
        
    Returns:
        Экономия в копейках (0 для тарифа на 1 месяц)
    """
    if months == 1:
        return 0
    
    # Получаем цену 1-месячного тарифа из БД
    tariffs = await queries.get_tariffs()
    
    # Ищем тариф на 1 месяц
    base_price = 29900  # значение по умолчанию
    for tariff in tariffs:
        if tariff["months"] == 1:
            base_price = tariff["price"]
            break
    
    # Расчет ожидаемой цены без скидки
    expected_price = base_price * months
    
    # Экономия = ожидаемая - реальная
    savings = expected_price - price
    
    return max(0, savings)


# ================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==================

async def get_user_purchase_info(user_id: int) -> dict:
    """
    Получение информации о покупках пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Словарь с информацией о покупках
    """
    # Получаем транзакции покупок
    transactions = await queries.get_user_transactions(user_id, limit=20)
    
    purchases = [tx for tx in transactions if tx["type"] == "purchase"]
    
    total_spent = sum(tx["amount"] for tx in purchases)
    
    return {
        "total_purchases": len(purchases),
        "total_spent": abs(total_spent),
        "last_purchase": purchases[0] if purchases else None
    }


async def check_user_can_purchase(user_id: int, tariff_id: int) -> tuple[bool, str]:
    """
    Проверка возможности покупки тарифа пользователем.
    
    Args:
        user_id: Telegram ID пользователя
        tariff_id: ID тарифа
        
    Returns:
        Кортеж (можно купить, сообщение об ошибке)
    """
    # Получаем пользователя
    user = await queries.get_user(user_id)
    
    if not user:
        return False, "Пользователь не найден"
    
    # Получаем тариф
    tariff = await queries.get_tariff(tariff_id)
    
    if not tariff:
        return False, "Тариф не найден"
    
    # Проверяем баланс
    if user["balance"] < tariff["price"]:
        return False, "Недостаточно средств"
    
    # Проверяем наличие серверов
    servers = await queries.get_active_servers()
    if not servers:
        return False, "Нет доступных серверов"
    
    return True, ""


# ================== ЭКСПОРТ ==================

__all__ = [
    "show_tariffs",
    "callback_buy_tariff",
    "callback_confirm_purchase",
    "callback_cancel_purchase",
    "callback_back_to_main",
    "calculate_savings",
    "get_user_purchase_info",
    "check_user_can_purchase",
]

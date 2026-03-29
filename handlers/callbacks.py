"""
Общие callback-обработчики.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from config import config
from database import queries
from utils.constants import (
    SUPPORT_MESSAGE, BOT_NAME,
    TOPUP_MENU_MESSAGE, TOPUP_ENTER_AMOUNT_MESSAGE, TOPUP_PAYMENT_DETAILS_MESSAGE,
    TOPUP_PENDING_MESSAGE, TOPUP_ADMIN_NOTIFICATION
)
from utils.helpers import format_balance
from keyboards import (
    get_support_keyboard, get_topup_menu_keyboard, get_topup_confirm_keyboard,
    get_back_to_main_keyboard, get_admin_topup_keyboard
)

router = Router()


class TopupStates(StatesGroup):
    enter_amount = State()


@router.callback_query(F.data == "close_message")
async def callback_close_message(callback: CallbackQuery):
    """Удаление сообщения по кнопке закрыть."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, db_user: dict = None):
    """Возврат в главное меню."""
    await callback.message.delete()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "back_to_key")
async def callback_back_to_key(callback: CallbackQuery, db_user: dict = None):
    """Возврат в раздел ключа."""
    await callback.message.delete()
    from handlers.keys import show_keys
    await show_keys(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "back_to_profile")
async def callback_back_to_profile(callback: CallbackQuery, db_user: dict = None):
    """Возврат в профиль."""
    await callback.message.delete()
    from handlers.profile import show_profile
    await show_profile(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "back_to_tariffs")
async def callback_back_to_tariffs(callback: CallbackQuery, db_user: dict = None):
    """Возврат к списку тарифов."""
    await callback.message.delete()
    from handlers.purchase import show_tariffs
    await show_tariffs(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "go_to_key")
async def callback_go_to_key(callback: CallbackQuery, db_user: dict = None):
    """Переход в раздел ключа."""
    await callback.message.delete()
    from handlers.keys import show_keys
    await show_keys(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "go_to_profile")
async def callback_go_to_profile(callback: CallbackQuery, db_user: dict = None):
    """Переход в профиль."""
    await callback.message.delete()
    from handlers.profile import show_profile
    await show_profile(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "check_payment")
async def callback_check_payment(callback: CallbackQuery, db_user: dict = None, bot: Bot = None):
    """Уведомление администратора об оплате."""
    user_id = callback.from_user.id
    
    # Отправляем уведомление всем админам
    sent_count = 0
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 Пользователь сообщил об оплате!\n\n"
                f"🆔 ID: {user_id}\n"
                f"👤 Username: @{callback.from_user.username or 'нет'}\n"
                f"📛 Имя: {db_user.get('full_name', 'не указано') if db_user else 'не указано'}\n"
                f"💰 Баланс: {format_balance(db_user.get('balance', 0)) if db_user else 0} ₽\n\n"
                f"Проверьте платеж и пополните баланс."
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    
    if sent_count > 0:
        await callback.answer(
            "✅ Уведомление отправлено администратору.\n"
            "Баланс будет пополнен в течение часа.",
            show_alert=True
        )
    else:
        await callback.answer(
            "⚠️ Не удалось отправить уведомление.\n"
            "Пожалуйста, напишите администратору вручную.",
            show_alert=True
        )


@router.callback_query(F.data == "show_faq")
async def callback_show_faq(callback: CallbackQuery):
    """Показ FAQ."""
    faq_text = """📌 Часто задаваемые вопросы

❓ Не подключается VPN?
→ Проверь правильность ключа
→ Попробуй другой сервер
→ Перезапусти приложение
→ Проверь интернет-соединение

❓ Как пополнить баланс?
→ Напиши @ShadowRing
→ Укажи сумму и получи реквизиты
→ После оплаты баланс пополнится в течение часа

❓ Как продлить подписку?
→ Зайди в "Купить / Продлить"
→ Выбери тариф
→ Подтверди покупку

❓ Можно ли использовать на нескольких устройствах?
→ Да, один ключ можно использовать 
  на нескольких устройствах одновременно

❓ Как сменить сервер?
→ Зайди в "Мой ключ"
→ Нажми "Сменить сервер"
→ Выбери новую локацию

❓ Что делать, если ключ не работает?
→ Напиши в поддержку @ShadowRing
→ Пришли свой ID и описание проблемы"""
    
    await callback.message.edit_text(faq_text)
    await callback.answer()


@router.callback_query(F.data == "back_to_support")
async def callback_back_to_support(callback: CallbackQuery):
    """Возврат в поддержку."""
    await callback.message.edit_text(
        SUPPORT_MESSAGE.format(bot_name=BOT_NAME),
        reply_markup=get_support_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_subscription_"))
async def callback_check_subscription(callback: CallbackQuery, db_user: dict = None):
    """Проверка подписки на канал."""
    action = callback.data.split("_")[2]
    
    is_subscribed = await queries.check_channel_subscription(
        callback.bot, 
        callback.from_user.id
    )
    
    if is_subscribed:
        await callback.answer("✅ Подписка подтверждена!", show_alert=True)
        
        # Выполняем действие в зависимости от параметра
        if action == "buy_trial":
            from handlers.start import callback_trial_get
            await callback_trial_get(callback, db_user)
        elif action == "buy_tariff":
            # Для других действий нужно передавать tariff_id
            await callback.answer("✅ Подписка подтверждена! Выберите тариф.", show_alert=True)
        elif action == "change_key":
            # Для смены ключа нужно передавать key_id
            await callback.answer("✅ Подписка подтверждена! Попробуйте снова.", show_alert=True)
        elif action == "enter_promocode":
            await callback.answer("✅ Подписка подтверждена! Введите промокод.", show_alert=True)
    else:
        await callback.answer("❌ Вы не подписаны на канал. Подпишитесь и попробуйте снова.", show_alert=True)


@router.callback_query(F.data == "balance_history")
async def callback_balance_history(callback: CallbackQuery, db_user: dict = None):
    """Показ истории операций."""
    user_id = callback.from_user.id
    
    transactions = await queries.get_user_transactions(user_id, limit=10)
    
    if not transactions:
        await callback.message.edit_text("📊 У вас пока нет операций.")
        await callback.answer()
        return
    
    from utils.constants import BALANCE_HISTORY_HEADER, BALANCE_HISTORY_ITEM, BALANCE_CURRENT
    from utils.helpers import format_datetime
    
    history_text = BALANCE_HISTORY_HEADER
    
    for tx in transactions:
        tx_type = tx.get("type", "unknown")
        tx_amount = tx.get("amount", 0)
        tx_balance = 0  # Нужно вычислить баланс на момент операции
        
        if tx_type == "payment":
            type_text = "💰 Пополнение"
            amount_text = f"+{tx_amount / 100:.2f}"
        elif tx_type == "purchase":
            type_text = "🛒 Покупка"
            amount_text = f"-{tx_amount / 100:.2f}"
        elif tx_type == "referral":
            type_text = "🎁 Реферальный"
            amount_text = f"+{tx_amount / 100:.2f}"
        elif tx_type == "admin":
            type_text = "👨‍💼 Админ"
            amount_text = f"+{tx_amount / 100:.2f}" if tx_amount > 0 else f"{tx_amount / 100:.2f}"
        elif tx_type == "admin_withdraw":
            type_text = "👨‍💼 Админ"
            amount_text = f"{tx_amount / 100:.2f}"
        elif tx_type == "promocode":
            type_text = "🎫 Промокод"
            amount_text = f"+{tx_amount / 100:.2f}"
        else:
            type_text = tx_type
            amount_text = f"{tx_amount / 100:.2f}"
        
        tx_date = format_datetime(tx.get("created_at"))
        history_text += BALANCE_HISTORY_ITEM.format(
            date=tx_date,
            type=type_text,
            amount=amount_text,
            balance=tx_balance
        )
    
    history_text += BALANCE_CURRENT.format(balance=format_balance(db_user.get("balance", 0)))
    
    await callback.message.edit_text(history_text)
    await callback.answer()


@router.callback_query(F.data == "enter_promocode")
async def callback_enter_promocode(callback: CallbackQuery, state: FSMContext):
    """Ввод промокода."""
    await callback.message.edit_text("<b>Введите ваш промокод:</b>")
    
    # Устанавливаем состояние для ввода промокода
    from handlers.promocode import PromocodeState
    await state.set_state(PromocodeState.entering_code)
    
    await callback.answer()


@router.callback_query(F.data == "refresh_servers_status")
async def callback_refresh_servers_status(callback: CallbackQuery):
    """Обновление статуса серверов."""
    from utils.constants import SERVERS_STATUS_MESSAGE
    
    servers = await queries.get_servers_with_load()
    
    servers_list = ""
    country_flags = {"NL": "🇳🇱", "DE": "🇩🇪", "FI": "🇫🇮", "US": "🇺🇸", "SG": "🇸🇬"}
    
    for server in servers:
        flag = country_flags.get(server.get("country_code", ""), "🌍")
        ping = server.get("ping", 0)
        load = server.get("load", 0)
        status = "🟢" if server.get("is_active") else "🔴"
        
        servers_list += f"{status} {flag} {server['name']} — {ping}ms (загруженность {load}%)\n"
    
    if not servers_list:
        servers_list = "Нет доступных серверов."
    
    await callback.message.edit_text(
        SERVERS_STATUS_MESSAGE.format(servers_list=servers_list)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("guide_key_"))
async def callback_guide_key(callback: CallbackQuery):
    """Инструкция по подключению."""
    guide_text = """📱 Инструкция по подключению:

🤖 Android:
1. Скачай v2RayTun из Google Play
2. Нажми "+" → "Импорт из буфера"
3. Вставь ключ
4. Нажми "Подключить"

🍏 iOS:
1. Скачай v2RayTun из App Store
2. Нажми "+" → "Импорт по ссылке"
3. Вставь ключ
4. Разреши установку VPN-профиля

💻 Windows/Mac:
Используй приложение Nekoray или V2RayN"""
    
    await callback.message.edit_text(guide_text)
    await callback.answer()


# ================== ПОПОЛНЕНИЕ БАЛАНСА ==================

@router.callback_query(F.data == "start_topup")
async def callback_start_topup(callback: CallbackQuery):
    """Показ меню пополнения баланса."""
    await callback.message.edit_text(TOPUP_MENU_MESSAGE, reply_markup=get_topup_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "start_topup_input")
async def callback_start_topup_input(callback: CallbackQuery, state: FSMContext):
    """Запрос суммы для пополнения."""
    min_topup = await queries.get_min_topup()
    await callback.message.edit_text(TOPUP_ENTER_AMOUNT_MESSAGE.format(min_amount=min_topup), reply_markup=None)
    await state.set_state(TopupStates.enter_amount)
    await callback.answer()


@router.message(TopupStates.enter_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    """Обработка ввода суммы пополнения."""
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
    
    await message.answer(
        TOPUP_PAYMENT_DETAILS_MESSAGE.format(amount=amount, payment_details=payment_details),
        reply_markup=get_topup_confirm_keyboard(amount)
    )
    await state.clear()


@router.callback_query(F.data.startswith("topup_paid_"))
async def callback_topup_paid(callback: CallbackQuery, bot: Bot):
    """Подтверждение оплаты."""
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    
    await queries.add_log(
        category="payment",
        action="topup_request",
        user_id=user_id,
        amount=amount * 100,
        details={"status": "pending"}
    )
    
    await callback.message.edit_text(TOPUP_PENDING_MESSAGE, reply_markup=get_back_to_main_keyboard())
    
    user_info = f"@{callback.from_user.username}" if callback.from_user.username else f"ID: {user_id}"
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                TOPUP_ADMIN_NOTIFICATION.format(user_info=user_info, amount=amount),
                reply_markup=get_admin_topup_keyboard(user_id, amount)
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    
    await callback.answer("✅ Заявка отправлена!")
    logger.info(f"Заявка на пополнение: user_id={user_id}, amount={amount}")

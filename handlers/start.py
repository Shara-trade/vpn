"""
Обработчик команды /start и стартового экрана (StarinaVPN).
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, timedelta

from config import config
from database import queries
from keyboards import (
    get_start_keyboard,
    get_main_keyboard,
    get_referral_keyboard,
    get_back_and_close_keyboard,
    get_subscription_check_keyboard,
)
from utils.constants import (
    START_MESSAGE,
    TRIAL_SUCCESS_MESSAGE,
    TRIAL_ALREADY_USED,
    REFERRAL_INVITE_MESSAGE,
    REFERRAL_BONUS_MESSAGE,
    BOT_NAME,
)
from utils.helpers import parse_referral_code, format_date, get_user_balance_rub
from services.xui_api import XuiService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: dict = None):
    """
    Обработка команды /start.
    Регистрирует пользователя, если он новый.
    Обрабатывает реферальный параметр в deep link.
    """
    await state.clear()
    
    user_id = message.from_user.id
    
    # Проверяем реферальный параметр
    referral_param = None
    if message.text and " " in message.text:
        param = message.text.split(" ", 1)[1].strip()
        referral_param = parse_referral_code(param)
    
    # Если пользователь новый и есть реферальный параметр
    if not db_user.get("referred_by") and referral_param:
        referrer = await queries.get_user(referral_param)
        
        if referrer and referrer["user_id"] != user_id:
            # Создаем реферальную связь сразу
            await queries.create_referral(referrer["user_id"], user_id)
            
            # Показываем сообщение о реферальном бонусе (+1 день)
            await message.answer(
                REFERRAL_INVITE_MESSAGE.format(
                    bot_name=BOT_NAME,
                    bonus_days=4  # 3 + 1
                ),
                reply_markup=get_referral_keyboard(referrer["user_id"])
            )
            return
    
    # Показываем главное меню
    await show_main_menu(message, db_user)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help."""
    help_text = f"""🦎 {BOT_NAME} — помощь

📌 Доступные команды:

/start — запуск бота
/help — эта справка
/profile — твой профиль и баланс
/keys — твои VPN ключи
/menu — главное меню

💡 Как начать пользоваться:

1. Нажми "Купить" в главном меню
2. Выбери "Пробный ключ" (3 дня бесплатно)
3. Скопируй полученный ключ
4. Установи приложение v2RayTun (iOS/Android)
5. Импортируй ключ и подключись!

💰 Пополнение баланса:
Перейди в Профиль → Пополнить баланс

💬 Вопросы? Пиши @StarinaVPN_Support_bot"""
    
    await message.answer(help_text)


@router.message(Command("profile"))
async def cmd_profile(message: Message, db_user: dict = None):
    """Обработка команды /profile."""
    from handlers.profile import show_profile
    await show_profile(message, db_user)


@router.message(Command("keys"))
async def cmd_keys(message: Message, db_user: dict = None):
    """Обработка команды /keys."""
    from handlers.keys import show_keys
    await show_keys(message, db_user)


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Обработка команды /support."""
    from utils.constants import SUPPORT_MESSAGE
    from keyboards import get_support_keyboard
    
    await message.answer(
        SUPPORT_MESSAGE.format(bot_name=BOT_NAME),
        reply_markup=get_support_keyboard()
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, db_user: dict = None):
    """Возврат в главное меню."""
    await show_main_menu(message, db_user)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, db_user: dict = None):
    """Отмена текущего действия."""
    await state.clear()
    
    await message.answer(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard()
    )


# ================== CALLBACK HANDLERS ==================

@router.callback_query(F.data == "trial_get")
async def callback_trial_get(callback: CallbackQuery, db_user: dict = None):
    """
    Активация пробного периода.
    Создает ключ в таблице user_keys (новая система множественных ключей).
    """
    user_id = callback.from_user.id
    
    # Проверяем подписку на канал
    is_subscribed = await check_channel_subscription(callback.bot, user_id)
    if not is_subscribed:
        await callback.message.edit_text(
            f"<b>Для активации пробного периода необходимо подписаться на новостной канал.</b>",
            reply_markup=get_subscription_check_keyboard("trial")
        )
        await callback.answer()
        return
    
    # Проверяем, использовал ли пользователь пробный период
    if db_user.get("trial_used"):
        await callback.answer(TRIAL_ALREADY_USED, show_alert=True)
        return
    
    # Проверяем лимит ключей (макс 5)
    from database.queries import get_user_keys_count
    keys_count = await get_user_keys_count(user_id)
    if keys_count >= 5:
        await callback.answer("❌ У вас уже 5 активных ключей. Удалите один, чтобы создать пробный.", show_alert=True)
        return
    
    # Получаем лучший сервер (автовыбор по нагрузке)
    server = await queries.select_best_server()
    
    if not server:
        await callback.answer("❌ Нет доступных серверов", show_alert=True)
        return
    
    # Создаем ключ через X-UI API
    xui = XuiService(server)
    
    try:
        # Проверяем реферальный бонус (+1 день)
        referral = await queries.get_referral_by_referral_id(user_id)
        trial_days = 4 if referral else 3
        
        key_data = await xui.create_client(user_id, days=trial_days)
        
        if not key_data:
            await callback.answer("❌ Ошибка при создании ключа", show_alert=True)
            return
        
        # Создаем запись в user_keys (новая система)
        from database.queries import create_user_key, increment_server_load
        await create_user_key(
            user_id=user_id,
            key=key_data["key"],
            key_uuid=key_data["uuid"],
            server_id=server["id"],
            expires_at=key_data["expires_at"],
            auto_renew=False
        )
        
        # Увеличиваем нагрузку сервера
        await increment_server_load(server["id"])
        
        # Отмечаем пробный период использованным
        await queries.set_trial_used(user_id)
        
        # Создаем транзакцию
        await queries.create_transaction(
            user_id=user_id,
            amount=0,
            transaction_type="trial",
            description=f"Пробный период {trial_days} дня"
        )
        
        # Логируем
        await queries.add_log(
            category="subscription",
            action="trial_activated",
            user_id=user_id,
            details={"server_id": server["id"], "days": trial_days}
        )
        
        # Отправляем сообщение с ключом
        await callback.message.edit_text(
            TRIAL_SUCCESS_MESSAGE.format(
                days=trial_days,
                server_name=server["name"],
                key=key_data["key"],
                expires_at=format_date(key_data["expires_at"])
            )
        )
        
        # Показываем главное меню
        await callback.message.answer(
            START_MESSAGE.format(bot_name=BOT_NAME),
            reply_markup=get_main_keyboard()
        )
        
        await callback.answer()
        logger.info(f"Пробный период активирован: user_id={user_id}, days={trial_days}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании пробного ключа: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "have_key")
async def callback_have_key(callback: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "У меня есть ключ".
    Запрашиваем у пользователя существующий ключ.
    """
    await callback.message.edit_text(
        "🔑 Отправь мне свой VLESS ключ, и я привяжу его к твоему аккаунту.\n\n"
        "Формат ключа:\n"
        "<code>vless://uuid@domain:port?...</code>",
        reply_markup=get_back_and_close_keyboard("back_to_main")
    )
    
    # Устанавливаем состояние ожидания ключа
    from handlers.key import WaitKeyState
    await state.set_state(WaitKeyState.waiting_key)
    
    await callback.answer()


@router.callback_query(F.data == "about_app")
async def callback_about_app(callback: CallbackQuery):
    """Информация о приложении v2RayTun."""
    about_text = """📱 О приложении v2RayTun

v2RayTun — это современный VPN-клиент для iOS и Android, 
поддерживающий протокол VLESS.

✅ Преимущества:
• Высокая скорость соединения
• Минимальное энергопотребление
• Простота настройки
• Стабильная работа

📲 Где скачать:

🤖 Android: Google Play
🍏 iOS: App Store

По запросу "v2RayTun" или "v2ray tun"."""
    
    await callback.message.edit_text(
        about_text,
        reply_markup=get_back_and_close_keyboard("back_to_main")
    )
    await callback.answer()


@router.callback_query(F.data == "servers_info")
async def callback_servers_info(callback: CallbackQuery):
    """Информация о выборе сервера."""
    servers_text = """❓ Как выбрать сервер?

🌍 Доступные локации:

🇳🇱 Амстердам (Нидерланды)
• Рекомендуем для СНГ
• Пинг: ~25 мс
• Стабильное соединение

🇩🇪 Франкфурт (Германия)
• Пинг: ~35 мс
• Хорошая скорость

🇫🇮 Хельсинки (Финляндия)
• Пинг: ~40 мс
• Близко к РФ

🇺🇸 Нью-Йорк (США)
• Пинг: ~90 мс
• Для доступа к US контенту

🇸🇬 Сингапур
• Пинг: ~120 мс
• Для Азиатского региона

💡 Совет: выбирай ближайший сервер 
для минимального пинга."""
    
    await callback.message.edit_text(
        servers_text,
        reply_markup=get_back_and_close_keyboard("back_to_main")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("activate_ref_"))
async def callback_activate_referral(callback: CallbackQuery, db_user: dict = None):
    """
    Активация реферального бонуса (+1 день к пробному периоду).
    Пробный ключ создается через раздел 'Купить'.
    """
    user_id = callback.from_user.id
    referrer_id = int(callback.data.split("_")[2])
    
    # Проверяем пригласившего
    referrer = await queries.get_user(referrer_id)
    if not referrer:
        await callback.answer("❌ Неверная реферальная ссылка", show_alert=True)
        return
    
    # Отмечаем реферальный бонус (увеличиваем trial_days на 1)
    # Фактически пробный ключ создается позже в разделе "Купить"
    await callback.message.edit_text(
        REFERRAL_BONUS_MESSAGE.format(total_days=4),
        reply_markup=get_back_to_main_keyboard()
    )

    # Логируем
    await queries.add_log(
        category="referral",
        action="referral_bonus_activated",
        user_id=user_id,
        details={"referrer_id": referrer_id, "bonus_days": 1}
    )

    logger.info(f"Реферальный бонус активирован: user_id={user_id}, referrer={referrer_id}")
    await callback.answer()


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def show_main_menu(message: Message, db_user: dict):
    """
    Показ главного меню пользователя (StarinaVPN).
    """
    from utils.constants import MAIN_MENU_MESSAGE
    from database.queries import get_user_keys_count
    
    # Получаем количество активных ключей
    active_keys = await get_user_keys_count(db_user["user_id"], active_only=True)
    
    # Получаем баланс
    balance = get_user_balance_rub(db_user.get("balance", 0))
    
    await message.answer(
        MAIN_MENU_MESSAGE.format(
            bot_name=BOT_NAME,
            active_keys=active_keys,
            balance=balance
        ),
        reply_markup=get_main_keyboard()
    )


async def check_channel_subscription(bot, user_id: int) -> bool:
    """
    Проверка подписки пользователя на новостной канал.
    
    Returns:
        True если подписан или проверка невозможна
    """
    try:
        from utils.constants import NEWS_CHANNEL
        if not NEWS_CHANNEL:
            return True
        
        channel = NEWS_CHANNEL.replace("@", "")
        member = await bot.get_chat_member(f"@{channel}", user_id)
        
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning(f"Не удалось проверить подписку: {e}")
        # Если канал недоступен или ошибка API - разрешаем действие
        return True

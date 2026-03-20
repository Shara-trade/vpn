"""
Обработчик команды /start и стартового экрана.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import config
from database import queries
from keyboards import (
    get_start_keyboard,
    get_main_keyboard,
    get_referral_keyboard,
)
from utils.constants import (
    START_MESSAGE,
    TRIAL_SUCCESS_MESSAGE,
    TRIAL_ALREADY_USED,
    REFERRAL_INVITE_MESSAGE,
    BOT_NAME,
)
from utils.helpers import parse_referral_code, format_date
from services.xui_api import XuiService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: dict = None):
    """
    Обработка команды /start.
    
    Регистрирует пользователя, если он новый.
    Обрабатывает реферальный параметр в deep link.
    """
    # Очищаем состояние
    await state.clear()
    
    user_id = message.from_user.id
    
    # Проверяем реферальный параметр
    referral_param = None
    if message.text and " " in message.text:
        param = message.text.split(" ", 1)[1].strip()
        referral_param = parse_referral_code(param)
    
    # Если пользователь еще не активировал реферал и есть реферальный параметр
    if not db_user.get("referred_by") and not db_user.get("trial_used") and referral_param:
        # Проверяем, существует ли пригласивший
        referrer = await queries.get_user(referral_param)
        
        if referrer and referrer["user_id"] != user_id:
            # Показываем сообщение о реферальном бонусе
            await message.answer(
                REFERRAL_INVITE_MESSAGE.format(
                    bot_name=BOT_NAME,
                    bonus_days=4
                ),
                reply_markup=get_referral_keyboard(referral_param)
            )
            return
    
    # Если у пользователя уже есть активная подписка
    if db_user.get("expires_at") and db_user.get("current_key"):
        await show_main_menu(message, db_user)
        return
    
    # Показываем стартовое меню
    await message.answer(
        START_MESSAGE.format(bot_name=BOT_NAME),
        reply_markup=get_start_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help."""
    help_text = f"""🦎 {BOT_NAME} — помощь

📌 Доступные команды:

/start — запуск бота
/help — эта справка
/profile — твой профиль
/key — твой VPN ключ
/support — связь с поддержкой

💡 Как начать пользоваться:

1. Нажми "Получить пробный период" на стартовом экране
2. Скопируй полученный ключ
3. Установи приложение v2RayTun (iOS/Android)
4. Импортируй ключ в приложение
5. Подключись!

💬 Вопросы? Пиши @FreakVPN_Support"""
    
    await message.answer(help_text)


@router.message(Command("profile"))
async def cmd_profile(message: Message, db_user: dict = None):
    """Обработка команды /profile."""
    from handlers.profile import show_profile
    await show_profile(message, db_user)


@router.message(Command("key"))
async def cmd_key(message: Message, db_user: dict = None):
    """Обработка команды /key."""
    from handlers.key import show_key
    await show_key(message, db_user)


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
    """
    user_id = callback.from_user.id
    
    # Проверяем, использовал ли пользователь пробный период
    if db_user.get("trial_used"):
        await callback.answer(TRIAL_ALREADY_USED, show_alert=True)
        return
    
    # Получаем триальный сервер
    server = await queries.get_trial_server()
    
    if not server:
        await callback.answer(
            "❌ Нет доступных серверов для пробного периода",
            show_alert=True
        )
        return
    
    # Создаем ключ через X-UI API
    xui = XuiService(server)
    
    try:
        # Генерируем ключ
        key_data = await xui.create_client(user_id, days=3)
        
        if not key_data:
            await callback.answer(
                "❌ Ошибка при создании ключа. Попробуйте позже.",
                show_alert=True
            )
            return
        
        # Сохраняем ключ и отмечаем пробный период
        await queries.set_user_key(user_id, key_data["key"], key_data["uuid"])
        await queries.set_user_server(user_id, server["id"])
        await queries.set_user_expires(
            user_id, 
            key_data["expires_at"]
        )
        await queries.set_trial_used(user_id)
        
        # Создаем транзакцию
        await queries.create_transaction(
            user_id=user_id,
            amount=0,
            transaction_type="trial",
            description="Пробный период 3 дня"
        )
        
        # Отправляем сообщение с ключом
        await callback.message.edit_text(
            TRIAL_SUCCESS_MESSAGE.format(
                days=3,
                server_name=server["name"],
                server_domain=server["domain"],
                key=key_data["key"],
                hours=72
            ),
            reply_markup=None
        )
        
        # Показываем главное меню
        await callback.message.answer(
            "🦎 Главное меню",
            reply_markup=get_main_keyboard()
        )
        
        await callback.answer()
        
        logger.info(f"Пробный период активирован: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании пробного ключа: {e}")
        await callback.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )


@router.callback_query(F.data == "have_key")
async def callback_have_key(callback: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "У меня есть ключ".
    Запрашиваем у пользователя существующий ключ.
    """
    await callback.message.edit_text(
        "🔑 Отправь мне свой VLESS ключ, и я привяжу его к твоему аккаунту.\n\n"
        "Формат ключа:\n"
        "<code>vless://uuid@domain:port?...</code>"
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
    
    await callback.message.edit_text(about_text)
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
    
    await callback.message.edit_text(servers_text)
    await callback.answer()


@router.callback_query(F.data.startswith("activate_ref_"))
async def callback_activate_referral(
    callback: CallbackQuery, 
    db_user: dict = None
):
    """
    Активация реферального бонуса.
    """
    user_id = callback.from_user.id
    
    # Извлекаем ID пригласившего
    referrer_id = int(callback.data.split("_")[2])
    
    # Проверяем, что пользователь еще не активировал бонус
    if db_user.get("trial_used"):
        await callback.answer(
            "❌ Ты уже активировал пробный период",
            show_alert=True
        )
        return
    
    # Проверяем пригласившего
    referrer = await queries.get_user(referrer_id)
    if not referrer:
        await callback.answer(
            "❌ Неверная реферальная ссылка",
            show_alert=True
        )
        return
    
    # Создаем реферальную связь
    await queries.create_referral(referrer_id, user_id)
    
    # Получаем триальный сервер
    server = await queries.get_trial_server()
    
    if not server:
        await callback.answer(
            "❌ Нет доступных серверов",
            show_alert=True
        )
        return
    
    # Создаем ключ на 4 дня (3 + 1 бонусный)
    xui = XuiService(server)
    
    try:
        key_data = await xui.create_client(user_id, days=4)
        
        if not key_data:
            await callback.answer(
                "❌ Ошибка при создании ключа",
                show_alert=True
            )
            return
        
        # Сохраняем данные
        await queries.set_user_key(user_id, key_data["key"], key_data["uuid"])
        await queries.set_user_server(user_id, server["id"])
        await queries.set_user_expires(user_id, key_data["expires_at"])
        await queries.set_trial_used(user_id)
        
        # Начисляем бонус пригласившему
        from config import config
        bonus = config.DEFAULT_REFERRAL_BONUS
        await queries.update_user_balance(referrer_id, bonus)
        
        # Обновляем заработок с рефералов
        from database.db import db
        await db.execute(
            "UPDATE users SET referral_earnings = referral_earnings + ? WHERE user_id = ?",
            (bonus, referrer_id)
        )
        await queries.set_referral_bonus_paid(user_id)
        
        # Создаем транзакции
        await queries.create_transaction(
            user_id=user_id,
            amount=0,
            transaction_type="trial",
            description="Пробный период 4 дня (с рефералом)"
        )
        
        await queries.create_transaction(
            user_id=referrer_id,
            amount=bonus,
            transaction_type="referral",
            description=f"Реферальный бонус за пользователя {user_id}"
        )
        
        # Отправляем сообщение
        await callback.message.edit_text(
            TRIAL_SUCCESS_MESSAGE.format(
                days=4,
                server_name=server["name"],
                server_domain=server["domain"],
                key=key_data["key"],
                hours=96
            )
        )
        
        await callback.message.answer(
            "🦎 Главное меню",
            reply_markup=get_main_keyboard()
        )
        
        # Уведомляем пригласившего
        try:
            await callback.bot.send_message(
                referrer_id,
                f"🎉 По твоей реферальной ссылке зарегистрировался новый пользователь!\n\n"
                f"💰 Тебе начислено {bonus // 100} ₽ на баланс."
            )
        except Exception:
            pass
        
        await callback.answer()
        
        logger.info(f"Реферальный бонус активирован: user_id={user_id}, referrer={referrer_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при активации реферала: {e}")
        await callback.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def show_main_menu(message: Message, db_user: dict):
    """
    Показ главного меню пользователя.
    """
    from utils.constants import MAIN_MENU_MESSAGE
    from utils.helpers import get_status_text, format_date
    
    # Определяем статус
    from datetime import datetime
    status = get_status_text(
        db_user.get("status", "active"),
        db_user.get("expires_at")
    )
    
    # Получаем сервер
    server_name = "Не выбран"
    if db_user.get("server_id"):
        server = await queries.get_server(db_user["server_id"])
        if server:
            server_name = server["name"]
    
    # Форматируем дату
    expires_at = "Не активна"
    if db_user.get("expires_at"):
        expires_at = format_date(db_user["expires_at"])
    
    await message.answer(
        MAIN_MENU_MESSAGE.format(
            bot_name=BOT_NAME,
            status=status,
            tariff="Премиум" if db_user.get("expires_at") else "Нет",
            expires_at=expires_at,
            server=server_name
        ),
        reply_markup=get_main_keyboard()
    )

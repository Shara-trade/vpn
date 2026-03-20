"""
Обработчики раздела 'Мой ключ'.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from database import queries
from keyboards import (
    get_key_keyboard,
    get_servers_keyboard,
    get_back_to_main_keyboard,
    get_main_keyboard,
    get_regenerate_confirm_keyboard,
)
from utils.constants import (
    KEY_MESSAGE,
    SERVER_SELECTED_MESSAGE,
    SERVERS_LIST_MESSAGE,
    BOT_NAME,
)
from utils.helpers import mask_key, parse_datetime, get_country_flag
from utils.validators import validate_vless_key
from services.xui_api import XuiService

router = Router()


class WaitKeyState(StatesGroup):
    """Состояние ожидания ввода ключа."""
    waiting_key = State()


class KeyStates(StatesGroup):
    """Состояния для работы с ключом."""
    confirm_regenerate = State()


async def show_key(message: Message, db_user: dict = None):
    """
    Показ ключа пользователя.
    """
    user_id = db_user["user_id"]
    
    # Проверяем, есть ли у пользователя ключ
    if not db_user.get("current_key"):
        await message.answer(
            "🔌 У тебя пока нет активного ключа.\n\n"
            "Нажми '🚀 Получить пробный период' на стартовом экране "
            "или купи тариф в разделе '💰 Купить / Продлить'.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Получаем сервер
    server_name = "Неизвестно"
    server_domain = ""
    
    if db_user.get("server_id"):
        server = await queries.get_server(db_user["server_id"])
        if server:
            server_name = server["name"]
            server_domain = server["domain"]
    
    # Отправляем ключ
    await message.answer(
        KEY_MESSAGE.format(
            bot_name=BOT_NAME,
            server_name=server_name,
            server_domain=server_domain,
            key=db_user["current_key"]
        ),
        reply_markup=get_key_keyboard()
    )


# ================== CALLBACK HANDLERS ==================

@router.callback_query(F.data == "go_to_key")
async def callback_go_to_key(callback: CallbackQuery, db_user: dict = None):
    """Переход в раздел ключа из inline-кнопки."""
    user_id = callback.from_user.id
    
    # Получаем актуальные данные
    db_user = await queries.get_user(user_id)
    
    # Удаляем предыдущее сообщение
    await callback.message.delete()
    
    # Показываем ключ
    await show_key(callback.message, db_user)
    
    await callback.answer()


@router.callback_query(F.data == "copy_key")
async def callback_copy_key(callback: CallbackQuery, db_user: dict = None):
    """
    Копирование ключа.
    Просто показываем уведомление, т.к. ключ уже в сообщении.
    """
    if db_user.get("current_key"):
        await callback.answer(
            "📋 Ключ скопирован в буфер обмена!\n"
            "Вставь его в приложение v2RayTun",
            show_alert=True
        )
    else:
        await callback.answer(
            "❌ У тебя нет активного ключа",
            show_alert=True
        )


@router.callback_query(F.data == "guide_ios")
async def callback_guide_ios(callback: CallbackQuery):
    """Инструкция для iOS."""
    guide = """🍏 Инструкция для iOS (v2RayTun)

1️⃣ Скачай v2RayTun из App Store

2️⃣ Открой приложение

3️⃣ Нажми "+" в правом верхнем углу

4️⃣ Выбери "Импорт по ссылке"

5️⃣ Вставь скопированный ключ

6️⃣ Нажми "Добавить"

7️⃣ Разреши добавление VPN-профиля

8️⃣ Переключи тумблер для подключения

✅ Готово! Ты подключен к VPN."""
    
    await callback.answer(guide, show_alert=True)


@router.callback_query(F.data == "guide_android")
async def callback_guide_android(callback: CallbackQuery):
    """Инструкция для Android."""
    guide = """🤖 Инструкция для Android (v2RayTun)

1️⃣ Скачай v2RayTun из Google Play

2️⃣ Открой приложение

3️⃣ Нажми "+" в правом нижнем углу

4️⃣ Выбери "Импорт из буфера"

5️⃣ Вставь скопированный ключ

6️⃣ Нажми "Сохранить"

7️⃣ Нажми на конфигурацию для подключения

8️⃣ Подтверди запрос на создание VPN

✅ Готово! Ты подключен к VPN."""
    
    await callback.answer(guide, show_alert=True)


@router.callback_query(F.data == "regenerate_key")
async def callback_regenerate_key(callback: CallbackQuery, state: FSMContext, db_user: dict = None):
    """Запрос подтверждения смены ключа."""
    await callback.message.edit_text(
        "⚠️ ВНИМАНИЕ!\n\n"
        "Ты собираешься сменить ключ доступа.\n"
        "Старый ключ перестанет работать МГНОВЕННО.\n"
        "Устройства придется настраивать заново.\n\n"
        "Продолжить?",
        reply_markup=get_regenerate_confirm_keyboard()
    )
    await state.set_state(KeyStates.confirm_regenerate)
    await callback.answer()


@router.callback_query(F.data == "confirm_regenerate", KeyStates.confirm_regenerate)
async def callback_confirm_regenerate(callback: CallbackQuery, state: FSMContext, db_user: dict = None):
    """
    Подтверждение смены ключа.
    """
    await state.clear()
    
    user_id = callback.from_user.id
    
    if not db_user.get("server_id"):
        await callback.answer(
            "❌ Сначала выбери сервер",
            show_alert=True
        )
        return
    
    # Получаем сервер
    server = await queries.get_server(db_user["server_id"])
    
    if not server:
        await callback.answer(
            "❌ Сервер не найден",
            show_alert=True
        )
        return
    
    await callback.answer(
        "🔄 Генерация нового ключа...",
        show_alert=False
    )
    
    try:
        # Удаляем старый ключ с сервера
        if db_user.get("key_uuid"):
            xui_old = XuiService(server)
            await xui_old.delete_client(db_user["key_uuid"])
        
        # Создаем новый ключ
        xui = XuiService(server)
        
        # Вычисляем оставшиеся дни
        expires_dt = parse_datetime(db_user.get("expires_at"))
        if expires_dt:
            days_left = (expires_dt - datetime.utcnow()).days
            days_left = max(1, days_left)
        else:
            days_left = 30
        
        key_data = await xui.create_client(user_id, days=days_left)
        
        if not key_data:
            await callback.answer(
                "❌ Ошибка при создании ключа",
                show_alert=True
            )
            return
        
        # Обновляем ключ в БД
        await queries.set_user_key(user_id, key_data["key"], key_data["uuid"])
        
        # Отправляем новый ключ
        await callback.message.edit_text(
            KEY_MESSAGE.format(
                bot_name=BOT_NAME,
                server_name=server["name"],
                server_domain=server["domain"],
                key=key_data["key"]
            ),
            reply_markup=get_key_keyboard()
        )
        
        await callback.answer(
            "✅ Новый ключ сгенерирован!",
            show_alert=True
        )

        logger.info(f"Ключ обновлен: user_id={user_id}")

    except Exception as e:
        logger.error(f"Ошибка при регенерации ключа: {e}")
        await callback.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )


@router.callback_query(F.data == "cancel_regenerate")
async def callback_cancel_regenerate(callback: CallbackQuery, state: FSMContext, db_user: dict = None):
    """Отмена смены ключа."""
    await state.clear()
    await callback.message.delete()
    await show_key(callback.message, db_user)
    await callback.answer("❌ Смена ключа отменена")


@router.callback_query(F.data == "change_server")
async def callback_change_server(callback: CallbackQuery, db_user: dict = None):
    """
    Показ списка серверов для смены.
    """
    # Получаем активные серверы
    servers = await queries.get_active_servers()
    
    if not servers:
        await callback.answer(
            "❌ Нет доступных серверов",
            show_alert=True
        )
        return
    
    # Формируем список серверов
    servers_list = ""
    for server in servers:
        flag = get_country_flag(server["country_code"])
        recommended = " (рекомендуем)" if server.get("load", 0) < 50 else ""
        servers_list += f"{flag} {server['name']} — {server.get('ping', 0)} ms{recommended}\n"
    
    await callback.message.edit_text(
        SERVERS_LIST_MESSAGE.format(servers_list=servers_list),
        reply_markup=get_servers_keyboard(servers, db_user.get("server_id"))
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("select_server_"))
async def callback_select_server(callback: CallbackQuery, db_user: dict = None):
    """
    Выбор нового сервера.
    """
    user_id = callback.from_user.id
    server_id = int(callback.data.split("_")[2])
    
    # Получаем сервер
    server = await queries.get_server(server_id)
    
    if not server:
        await callback.answer(
            "❌ Сервер не найден",
            show_alert=True
        )
        return
    
    try:
        # Удаляем старый ключ с предыдущего сервера
        if db_user.get("server_id") and db_user.get("key_uuid"):
            old_server = await queries.get_server(db_user["server_id"])
            if old_server:
                xui_old = XuiService(old_server)
                await xui_old.delete_client(db_user["key_uuid"])
        
        # Создаем новый ключ на новом сервере
        xui = XuiService(server)
        
        # Вычисляем оставшиеся дни
        expires_dt = parse_datetime(db_user.get("expires_at"))
        if expires_dt:
            days_left = (expires_dt - datetime.utcnow()).days
            days_left = max(1, days_left)
        else:
            days_left = 30
        
        key_data = await xui.create_client(user_id, days=days_left)
        
        if not key_data:
            await callback.answer(
                "❌ Ошибка при создании ключа на сервере",
                show_alert=True
            )
            return
        
        # Обновляем данные в БД
        await queries.set_user_key(user_id, key_data["key"], key_data["uuid"])
        await queries.set_user_server(user_id, server_id)
        
        # Отправляем сообщение
        await callback.message.edit_text(
            SERVER_SELECTED_MESSAGE.format(
                server_name=f"{get_country_flag(server['country_code'])} {server['name']}",
                key=key_data["key"]
            ),
            reply_markup=get_back_to_main_keyboard()
        )
        
        await callback.answer(
            "✅ Сервер изменен!",
            show_alert=False
        )
        
        logger.info(f"Сервер изменен: user_id={user_id}, server={server['name']}")
        
    except Exception as e:
        logger.error(f"Ошибка при смене сервера: {e}")
        await callback.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )


# ================== ОБРАБОТКА ВВОДА КЛЮЧА ==================

@router.message(WaitKeyState.waiting_key)
async def process_user_key(message: Message, state: FSMContext, db_user: dict = None):
    """
    Обработка введенного пользователем ключа.
    """
    user_id = message.from_user.id
    key = message.text.strip()
    
    # Валидируем ключ
    if not validate_vless_key(key):
        await message.answer(
            "❌ Неверный формат ключа.\n\n"
            "Ключ должен начинаться с vless://\n"
            "Попробуй еще раз или напиши в поддержку."
        )
        return
    
    # Парсим ключ для извлечения данных
    # Формат: vless://uuid@domain:port?security=tls&type=tcp#name
    
    try:
        parsed = urlparse(key)
        uuid = parsed.username
        domain = parsed.hostname
        port = parsed.port or 443
        
        # Ищем сервер по домену
        servers = await queries.get_active_servers()
        matched_server = None
        
        for server in servers:
            if server["domain"] == domain:
                matched_server = server
                break
        
        if not matched_server:
            await message.answer(
                "❌ Сервер из этого ключа не найден в нашей системе.\n\n"
                "Возможно, ключ от другого VPN-сервиса.\n"
                "Получи новый ключ через пробный период или покупку тарифа."
            )
            await state.clear()
            return
        
        # Сохраняем ключ
        await queries.set_user_key(user_id, key, uuid)
        await queries.set_user_server(user_id, matched_server["id"])
        
        await message.answer(
            "✅ Ключ успешно привязан к твоему аккаунту!\n\n"
            "Теперь ты можешь управлять им в разделе '🔌 Мой ключ'.",
            reply_markup=get_main_keyboard()
        )
        
        await state.clear()
        
        logger.info(f"Ключ привязан: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ключа: {e}")
        await message.answer(
            "❌ Не удалось обработать ключ.\n\n"
            "Проверь правильность и попробуй еще раз."
        )



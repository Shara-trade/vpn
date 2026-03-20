"""
Обработчики админ-панели FreakVPN.
Все функции управления ботом для администраторов.
"""

import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from loguru import logger

from config import config
from database import queries, db
from keyboards import (
    get_admin_keyboard,
    get_cancel_keyboard,
)
from keyboards.admin import (
    get_user_actions_keyboard,
    get_admin_balance_confirm_keyboard,
    get_admin_servers_keyboard,
    get_server_actions_keyboard,
    get_admin_mailing_keyboard,
    get_admin_settings_keyboard,
    get_admin_tariffs_keyboard,
    get_admin_cancel_keyboard,
    get_admin_back_keyboard,
)
from utils.constants import (
    ADMIN_WELCOME_MESSAGE,
    ADMIN_USER_INFO,
    ADMIN_BALANCE_ADDED,
    ADMIN_USER_BALANCE_ADDED,
    ADMIN_STATS_MESSAGE,
    ADMIN_SERVERS_MESSAGE,
    ADMIN_SETTINGS_MESSAGE,
    BOT_NAME,
)
from utils.helpers import format_balance, format_date, format_datetime, mask_key, parse_datetime, get_country_flag
from services.xui_api import XuiService, check_server_connection

router = Router()


# ================== СОСТОЯНИЯ FSM ==================

class AdminStates(StatesGroup):
    """Состояния для админ-операций."""
    
    # Пользователи
    search_user = State()
    add_balance_amount = State()
    extend_days = State()
    
    # Серверы
    add_server = State()
    edit_server = State()
    
    # Рассылка
    mailing_content = State()
    
    # Настройки
    edit_tariff_price = State()
    edit_trial_days = State()
    edit_contacts = State()


# ================== ПРОВЕРКА ПРАВ АДМИНА ==================

def is_admin(user_id: int) -> bool:
    """
    Проверка, является ли пользователь администратором.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        True если пользователь админ
    """
    return user_id in config.ADMIN_IDS


# ================== КОМАНДА /admin ==================

@router.message(F.text == "/admin")
async def cmd_admin(message: Message):
    """
    Вход в админ-панель.
    Если пользователь не админ - полное игнорирование.
    """
    user_id = message.from_user.id
    
    # Проверяем права
    if not is_admin(user_id):
        # Полное игнорирование для не-админов
        return
    
    # Отправляем приветствие
    await message.answer(
        ADMIN_WELCOME_MESSAGE.format(bot_name=BOT_NAME),
        reply_markup=get_admin_keyboard()
    )
    
    logger.info(f"Админ вошел в панель: user_id={user_id}")


# ================== РАЗДЕЛ ПОЛЬЗОВАТЕЛИ ==================

@router.message(F.text == "👥 Пользователи")
async def admin_users(message: Message, state: FSMContext):
    """Поиск пользователя."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    await message.answer(
        "🔍 Введи ID или @username пользователя для поиска:",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.search_user)


@router.message(AdminStates.search_user)
async def admin_search_user(message: Message, state: FSMContext):
    """Обработка поиска пользователя."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    query = message.text.strip()
    
    # Ищем пользователя
    user = None
    
    # Пробуем как ID
    if query.isdigit():
        user = await queries.get_user(int(query))
    
    # Пробуем как username
    if not user:
        user = await queries.get_user_by_username(query)
    
    if not user:
        await message.answer(
            "❌ Пользователь не найден.\n\n"
            "Попробуй другой ID или username:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Сохраняем найденного пользователя
    await state.update_data(target_user_id=user["user_id"])
    
    # Получаем сервер
    server_name = "Не выбран"
    if user.get("server_id"):
        server = await queries.get_server(user["server_id"])
        if server:
            server_name = server["name"]
    
    # Формируем информацию
    status = "Активен" if user.get("status") == "active" else user.get("status", "Неизвестно")
    if user.get("expires_at"):
        expires_dt = parse_datetime(user["expires_at"])
        if expires_dt and expires_dt > datetime.utcnow():
            status = f"Активен до {format_date(user['expires_at'])}"
        else:
            status = "Истек"
    
    key_preview = mask_key(user.get("current_key", "Нет"))
    
    await message.answer(
        ADMIN_USER_INFO.format(
            username=f"@{user['username']}" if user.get("username") else "Нет username",
            user_id=user["user_id"],
            registered_at=format_date(user.get("registered_at")),
            status=status,
            server=server_name,
            balance=format_balance(user.get("balance", 0)),
            key_preview=key_preview
        ),
        reply_markup=get_user_actions_keyboard(user["user_id"])
    )
    
    await state.clear()


# ================== ДЕЙСТВИЯ С ПОЛЬЗОВАТЕЛЕМ ==================

@router.callback_query(F.data.startswith("admin_add_balance_"))
async def callback_admin_add_balance(callback: CallbackQuery, state: FSMContext):
    """Начало пополнения баланса."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[3])
    
    await state.update_data(target_user_id=user_id)
    
    user = await queries.get_user(user_id)
    
    await callback.message.edit_text(
        f"💰 Пополнение баланса\n\n"
        f"ID: {user_id}\n"
        f"@{user['username'] if user.get('username') else 'Нет username'}\n"
        f"Текущий баланс: {format_balance(user.get('balance', 0))} ₽\n\n"
        f"Введи сумму для начисления (в рублях):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_balance_amount)
    await callback.answer()


@router.message(AdminStates.add_balance_amount)
async def admin_process_balance_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    # Валидируем сумму
    from utils.validators import validate_amount
    is_valid, amount_kopecks = validate_amount(message.text)
    
    if not is_valid:
        await message.answer(
            "❌ Неверная сумма. Введи число (например: 500):",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    
    user = await queries.get_user(target_user_id)
    current_balance = user.get("balance", 0)
    new_balance = current_balance + amount_kopecks
    
    await state.update_data(amount=amount_kopecks)
    
    await message.answer(
        f"Начислить {format_balance(amount_kopecks)} ₽ пользователю?\n\n"
        f"@{user['username'] if user.get('username') else 'ID: ' + str(target_user_id)}\n"
        f"Текущий баланс: {format_balance(current_balance)} ₽\n"
        f"Новый баланс: {format_balance(new_balance)} ₽",
        reply_markup=get_admin_balance_confirm_keyboard(amount_kopecks, target_user_id)
    )


@router.callback_query(F.data.startswith("admin_confirm_add_"))
async def callback_admin_confirm_add(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение начисления баланса."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split("_")
    amount = int(parts[3])
    target_user_id = int(parts[4])
    
    admin_id = callback.from_user.id
    
    # Начисляем баланс
    new_balance = await queries.update_user_balance(target_user_id, amount)
    
    # Создаем транзакцию
    await queries.create_transaction(
        user_id=target_user_id,
        amount=amount,
        transaction_type="admin",
        description="Пополнение от администратора",
        admin_id=admin_id
    )
    
    # Получаем пользователя
    user = await queries.get_user(target_user_id)
    
    # Сообщение админу
    await callback.message.edit_text(
        ADMIN_BALANCE_ADDED.format(
            amount=format_balance(amount),
            new_balance=format_balance(new_balance)
        )
    )
    
    # Уведомление пользователю
    try:
        await bot.send_message(
            target_user_id,
            ADMIN_USER_BALANCE_ADDED.format(
                amount=format_balance(amount),
                balance=format_balance(new_balance),
                bot_name=BOT_NAME
            )
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {target_user_id}: {e}")
    
    await state.clear()
    await callback.answer("✅ Баланс пополнен")
    
    logger.info(
        f"Админ пополнил баланс: admin={admin_id}, user={target_user_id}, amount={amount}"
    )


@router.callback_query(F.data.startswith("admin_extend_"))
async def callback_admin_extend(callback: CallbackQuery, state: FSMContext):
    """Продление подписки пользователю."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[2])
    
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        "➕ Продление подписки\n\n"
        "Введи количество дней для продления:",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.extend_days)
    await callback.answer()


@router.message(AdminStates.extend_days)
async def admin_process_extend_days(message: Message, state: FSMContext):
    """Обработка продления дней."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            "❌ Неверное количество дней. Введи число:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    
    user = await queries.get_user(target_user_id)
    
    # Вычисляем новую дату
    expires_dt = parse_datetime(user.get("expires_at"))
    if expires_dt and expires_dt > datetime.utcnow():
        new_expires = expires_dt + timedelta(days=days)
    else:
        new_expires = datetime.utcnow() + timedelta(days=days)
    
    # Обновляем
    await queries.set_user_expires(target_user_id, new_expires)
    await queries.set_user_status(target_user_id, "active")
    
    await message.answer(
        f"✅ Подписка продлена!\n\n"
        f"Пользователь: @{user['username'] if user.get('username') else target_user_id}\n"
        f"Добавлено дней: {days}\n"
        f"Новая дата истечения: {format_date(new_expires)}",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()
    
    logger.info(f"Админ продлил подписку: user={target_user_id}, days={days}")


@router.callback_query(F.data.startswith("admin_block_"))
async def callback_admin_block(callback: CallbackQuery, bot: Bot):
    """Блокировка пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[2])
    admin_id = callback.from_user.id
    
    user = await queries.get_user(user_id)
    
    if user.get("status") == "blocked":
        # Разблокируем
        await queries.set_user_status(user_id, "active")
        await callback.answer("✅ Пользователь разблокирован", show_alert=True)
        
        # Обновляем кнопки
        await callback.message.edit_reply_markup(
            reply_markup=get_user_actions_keyboard(user_id)
        )
    else:
        # Блокируем
        await queries.set_user_status(user_id, "blocked")
        
        # Удаляем ключ с сервера
        if user.get("key_uuid") and user.get("server_id"):
            server = await queries.get_server(user["server_id"])
            if server:
                try:
                    xui = XuiService(server)
                    await xui.delete_client(user["key_uuid"])
                except Exception as e:
                    logger.error(f"Ошибка удаления ключа: {e}")
        
        await callback.answer("✅ Пользователь заблокирован", show_alert=True)
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                user_id,
                "❌ Твой доступ к VPN был заблокирован администратором.\n\n"
                "Если считаешь это ошибкой, напиши в поддержку."
            )
        except Exception:
            pass
    
    logger.info(f"Админ изменил статус: user={user_id}, admin={admin_id}")


@router.callback_query(F.data.startswith("admin_reset_key_"))
async def callback_admin_reset_key(callback: CallbackQuery):
    """Сброс ключа пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[3])
    
    user = await queries.get_user(user_id)
    
    if not user.get("server_id"):
        await callback.answer("❌ У пользователя нет сервера", show_alert=True)
        return
    
    server = await queries.get_server(user["server_id"])
    
    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return
    
    try:
        # Удаляем старый ключ
        if user.get("key_uuid"):
            xui_old = XuiService(server)
            await xui_old.delete_client(user["key_uuid"])
        
        # Создаем новый
        xui = XuiService(server)
        
        # Вычисляем оставшиеся дни
        days = 30
        expires_dt = parse_datetime(user.get("expires_at"))
        if expires_dt:
            days_left = (expires_dt - datetime.utcnow()).days
            days = max(1, days_left)
        
        key_data = await xui.create_client(user_id, days=days)
        
        if key_data:
            await queries.set_user_key(user_id, key_data["key"], key_data["uuid"])
            
            await callback.answer(
                f"✅ Новый ключ создан!\n\n"
                f"UUID: {key_data['uuid'][:20]}...",
                show_alert=True
            )
        else:
            await callback.answer("❌ Ошибка создания ключа", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка сброса ключа: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_history_"))
async def callback_admin_history(callback: CallbackQuery):
    """История операций пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[2])
    
    transactions = await queries.get_user_transactions(user_id, limit=15)
    
    if not transactions:
        await callback.answer("📊 История пуста", show_alert=True)
        return
    
    text = "📊 История операций:\n\n"
    
    type_names = {
        "payment": "💳 Пополнение",
        "purchase": "🛒 Покупка",
        "referral": "🎁 Реферал",
        "admin": "👤 Админ",
        "trial": "🆓 Пробный",
    }
    
    for tx in transactions[:10]:
        tx_type = type_names.get(tx["type"], tx["type"])
        amount = tx["amount"] / 100
        sign = "+" if tx["amount"] >= 0 else ""
        
        text += f"{format_datetime(tx['created_at'])} — {tx_type}: {sign}{amount:.0f} ₽\n"
    
    await callback.message.answer(text)
    await callback.answer()


# ================== РАЗДЕЛ СТАТИСТИКА ==================

@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    """Показ статистики."""
    if not is_admin(message.from_user.id):
        return
    
    # Получаем статистику
    total_users = await queries.get_users_count()
    active_today = await queries.get_active_users_today()
    new_today = await queries.get_new_users_today()
    total_balance = await queries.get_total_balance()
    month_sales = await queries.get_month_sales()
    avg_check = await queries.get_avg_check()
    
    # Статистика по серверам
    servers_stats = await queries.get_servers_stats()
    
    servers_text = ""
    for stat in servers_stats:
        flag = get_country_flag(stat["country_code"])
        status = "✅" if stat["is_active"] else "❌"
        servers_text += f"{flag} {stat['name']}: {stat['users_count']} польз.\n"
    
    await message.answer(
        ADMIN_STATS_MESSAGE.format(
            bot_name=BOT_NAME,
            total_users=total_users,
            active_today=active_today,
            new_today=new_today,
            total_balance=format_balance(total_balance),
            month_sales=format_balance(month_sales),
            avg_check=format_balance(avg_check),
            servers_stats=servers_text or "Нет серверов"
        )
    )


# ================== РАЗДЕЛ СЕРВЕРЫ ==================

@router.message(F.text == "🌍 Серверы")
async def admin_servers(message: Message, state: FSMContext):
    """Управление серверами."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    servers = await queries.get_active_servers()
    all_servers = await db.fetchall("SELECT * FROM servers ORDER BY name")
    
    # Формируем список
    servers_list = ""
    for server in all_servers:
        status = "✅" if server["is_active"] else "❌"
        flag = get_country_flag(server["country_code"])
        servers_list += f"{status} {flag} {server['name']} ({server['domain']})\n"
    
    # Считаем пользователей по серверам
    users_by_server = ""
    server_stats = await queries.get_servers_stats()
    for stat in server_stats:
        if stat["users_count"] > 0:
            flag = get_country_flag(stat["country_code"])
            users_by_server += f"{flag} {stat['name']}: {stat['users_count']} польз.\n"
    
    await message.answer(
        ADMIN_SERVERS_MESSAGE.format(
            servers_list=servers_list or "Нет серверов",
            users_by_server=users_by_server or "Нет пользователей"
        ),
        reply_markup=get_admin_servers_keyboard(all_servers)
    )


@router.callback_query(F.data == "admin_add_server")
async def callback_admin_add_server(callback: CallbackQuery, state: FSMContext):
    """Добавление нового сервера."""
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "➕ Добавление нового сервера\n\n"
        "Введи данные в формате:\n"
        "Название;Страна;Домен;IP;X-UI порт;Логин;Пароль\n\n"
        "Пример:\n"
        "Амстердам;NL;ams.freakvpn.ru;45.67.89.10;54321;admin;pass123",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_server)
    await callback.answer()


@router.message(AdminStates.add_server)
async def admin_process_add_server(message: Message, state: FSMContext):
    """Обработка добавления сервера."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    from utils.validators import validate_server_data
    
    is_valid, data = validate_server_data(message.text)
    
    if not is_valid:
        await message.answer(
            "❌ Неверный формат данных.\n\n"
            "Используй формат:\n"
            "Название;Страна;Домен;IP;X-UI порт;Логин;Пароль",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    # Формируем API URL
    api_url = f"http://{data['ip']}:{data['port']}"
    
    # Проверяем подключение
    server_check = {
        "api_url": api_url,
        "api_username": data["login"],
        "api_password": data["password"]
    }
    
    await message.answer("🔄 Проверка подключения к серверу...")
    
    is_connected = await check_server_connection(server_check)
    
    if not is_connected:
        await message.answer(
            "❌ Не удалось подключиться к X-UI панели.\n\n"
            "Проверь данные и попробуй снова.",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    # Добавляем сервер в БД
    server_id = await queries.create_server(
        name=data["name"],
        country_code=data["country_code"],
        domain=data["domain"],
        ip=data["ip"],
        api_url=api_url,
        api_username=data["login"],
        api_password=data["password"],
        port=443,
        inbound_id=1
    )
    
    await message.answer(
        f"✅ Сервер успешно добавлен!\n\n"
        f"ID: {server_id}\n"
        f"Название: {data['name']}\n"
        f"Домен: {data['domain']}\n"
        f"Статус: ✅ Подключен",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()
    
    logger.info(f"Админ добавил сервер: {data['name']} ({data['domain']})")


@router.callback_query(F.data == "admin_check_servers")
async def callback_admin_check_servers(callback: CallbackQuery):
    """Проверка статуса серверов."""
    if not is_admin(callback.from_user.id):
        return
    
    servers = await queries.get_active_servers()
    
    await callback.answer("🔄 Проверка серверов...", show_alert=False)
    
    results = []
    
    for server in servers:
        is_ok = await check_server_connection(server)
        status = "✅" if is_ok else "❌"
        flag = get_country_flag(server["country_code"])
        results.append(f"{status} {flag} {server['name']}: {'OK' if is_ok else 'OFFLINE'}")
    
    text = "🔄 Статус серверов:\n\n" + "\n".join(results)
    
    await callback.message.answer(text)
    await callback.answer()


# ================== РАЗДЕЛ РАССЫЛКА ==================

@router.message(F.text == "✉️ Рассылка")
async def admin_mailing(message: Message, state: FSMContext):
    """Создание рассылки."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    await message.answer(
        "📨 Создание рассылки\n\n"
        "Отправь мне сообщение (текст, фото или видео), "
        "которое хочешь разослать всем пользователям.",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.mailing_content)


@router.message(AdminStates.mailing_content)
async def admin_process_mailing_content(message: Message, state: FSMContext):
    """Обработка контента для рассылки."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    # Сохраняем контент
    content_type = None
    content = None
    
    if message.text:
        content_type = "text"
        content = message.text
    elif message.photo:
        content_type = "photo"
        content = message.photo[-1].file_id
        await state.update_data(caption=message.caption)
    elif message.video:
        content_type = "video"
        content = message.video.file_id
        await state.update_data(caption=message.caption)
    
    if not content:
        await message.answer(
            "❌ Не удалось получить контент. Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(content_type=content_type, content=content)
    
    # Считаем пользователей
    total_users = await queries.get_users_count()
    
    await message.answer(
        f"📨 Предпросмотр рассылки:\n\n"
        f"(сообщение выше)\n\n"
        f"Будет отправлено: {total_users} пользователям",
        reply_markup=get_admin_mailing_keyboard(total_users)
    )


@router.callback_query(F.data == "admin_send_test")
async def callback_admin_send_test(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Тестовая отправка рассылки себе."""
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    content_type = data.get("content_type")
    content = data.get("content")
    caption = data.get("caption")
    
    admin_id = callback.from_user.id
    
    try:
        if content_type == "text":
            await bot.send_message(admin_id, content)
        elif content_type == "photo":
            await bot.send_photo(admin_id, content, caption=caption)
        elif content_type == "video":
            await bot.send_video(admin_id, content, caption=caption)
        
        await callback.answer("✅ Тестовое сообщение отправлено тебе", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_send_all")
async def callback_admin_send_all(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Отправка рассылки всем пользователям."""
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    content_type = data.get("content_type")
    content = data.get("content")
    caption = data.get("caption")
    
    admin_id = callback.from_user.id
    
    await callback.message.edit_text("🔄 Рассылка запущена...")
    
    # Получаем всех пользователей
    users = await queries.get_all_users()
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            if content_type == "text":
                await bot.send_message(user["user_id"], content)
            elif content_type == "photo":
                await bot.send_photo(user["user_id"], content, caption=caption)
            elif content_type == "video":
                await bot.send_video(user["user_id"], content, caption=caption)
            
            sent += 1
            
            # Небольшая задержка чтобы не попасть в rate limit
            await asyncio.sleep(0.05)
            
        except Exception:
            failed += 1
    
    await callback.message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"Отправлено: {sent}\n"
        f"Не удалось отправить: {failed}"
    )
    
    await state.clear()
    
    logger.info(f"Рассылка завершена: admin={admin_id}, sent={sent}, failed={failed}")


# ================== РАЗДЕЛ НАСТРОЙКИ ==================

@router.message(F.text == "⚙️ Настройки")
async def admin_settings(message: Message, state: FSMContext):
    """Панель настроек."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    # Получаем тарифы
    tariffs = await queries.get_tariffs()
    
    # Получаем настройки
    trial_days = await queries.get_setting("trial_days")
    referral_bonus = await queries.get_setting("referral_bonus")
    
    # Формируем сообщение
    price_1 = tariffs[0]["price"] // 100 if len(tariffs) > 0 else 0
    price_3 = tariffs[1]["price"] // 100 if len(tariffs) > 1 else 0
    price_6 = tariffs[2]["price"] // 100 if len(tariffs) > 2 else 0
    price_12 = tariffs[3]["price"] // 100 if len(tariffs) > 3 else 0
    
    await message.answer(
        ADMIN_SETTINGS_MESSAGE.format(
            price_1=price_1,
            price_3=price_3,
            price_6=price_6,
            price_12=price_12,
            trial_days=trial_days or "3",
            referral_bonus=format_balance(int(referral_bonus or "5000"))
        ),
        reply_markup=get_admin_settings_keyboard()
    )


@router.callback_query(F.data == "admin_edit_prices")
async def callback_admin_edit_prices(callback: CallbackQuery, state: FSMContext):
    """Редактирование тарифов."""
    if not is_admin(callback.from_user.id):
        return
    
    tariffs = await queries.get_tariffs()
    
    await callback.message.edit_text(
        "✏️ Выбери тариф для редактирования цены:",
        reply_markup=get_admin_tariffs_keyboard(tariffs)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_tariff_"))
async def callback_admin_edit_tariff(callback: CallbackQuery, state: FSMContext):
    """Выбор тарифа для редактирования."""
    if not is_admin(callback.from_user.id):
        return
    
    tariff_id = int(callback.data.split("_")[3])
    
    await state.update_data(tariff_id=tariff_id)
    
    tariff = await queries.get_tariff(tariff_id)
    
    await callback.message.edit_text(
        f"✏️ Редактирование тарифа: {tariff['name']}\n\n"
        f"Текущая цена: {tariff['price'] // 100} ₽\n\n"
        f"Введи новую цену в рублях:",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.edit_tariff_price)
    await callback.answer()


@router.message(AdminStates.edit_tariff_price)
async def admin_process_tariff_price(message: Message, state: FSMContext):
    """Обработка новой цены тарифа."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    from utils.validators import validate_amount
    is_valid, price_kopecks = validate_amount(message.text)
    
    if not is_valid:
        await message.answer(
            "❌ Неверная цена. Введи число:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    tariff_id = data["tariff_id"]
    
    await queries.update_tariff_price(tariff_id, price_kopecks)
    
    tariff = await queries.get_tariff(tariff_id)
    
    await message.answer(
        f"✅ Цена тарифа '{tariff['name']}' обновлена!\n\n"
        f"Новая цена: {price_kopecks // 100} ₽",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()
    
    logger.info(f"Админ изменил цену тарифа: tariff_id={tariff_id}, price={price_kopecks}")


@router.callback_query(F.data == "admin_edit_trial")
async def callback_admin_edit_trial(callback: CallbackQuery, state: FSMContext):
    """Редактирование пробного периода."""
    if not is_admin(callback.from_user.id):
        return
    
    current = await queries.get_setting("trial_days") or "3"
    
    await callback.message.edit_text(
        f"✏️ Редактирование пробного периода\n\n"
        f"Текущее значение: {current} дней\n\n"
        f"Введи новое количество дней:",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.edit_trial_days)
    await callback.answer()


@router.message(AdminStates.edit_trial_days)
async def admin_process_trial_days(message: Message, state: FSMContext):
    """Обработка нового пробного периода."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            "❌ Неверное количество дней. Введи число:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    await queries.update_setting("trial_days", str(days))
    
    await message.answer(
        f"✅ Пробный период обновлен!\n\n"
        f"Новое значение: {days} дней",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()


@router.callback_query(F.data == "admin_edit_contacts")
async def callback_admin_edit_contacts(callback: CallbackQuery, state: FSMContext):
    """Редактирование контактов."""
    if not is_admin(callback.from_user.id):
        return
    
    support = await queries.get_setting("support_contact") or "@FreakVPN_Support"
    payment = await queries.get_setting("payment_contact") or "@FreakVPN_Shop"
    
    await callback.message.edit_text(
        f"✏️ Редактирование контактов\n\n"
        f"Текущие контакты:\n"
        f"• Поддержка: {support}\n"
        f"• Оплата: {payment}\n\n"
        f"Для изменения контактов отредактируй их в файле .env "
        f"или напрямую в базе данных.",
        reply_markup=get_admin_back_keyboard("admin_settings")
    )
    
    await callback.answer()


# ================== ОТМЕНА ДЕЙСТВИЯ ==================

@router.callback_query(F.data == "admin_cancel")
async def callback_admin_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Действие отменено"
    )
    
    await callback.answer()


@router.message(F.text == "❌ Отмена")
async def admin_cancel_message(message: Message, state: FSMContext):
    """Отмена через Reply-кнопку."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    await message.answer(
        "❌ Действие отменено",
        reply_markup=get_admin_keyboard()
    )


# ================== АКТИВАЦИЯ/ДЕАКТИВАЦИЯ СЕРВЕРОВ ==================

@router.callback_query(F.data.startswith("admin_server_activate_"))
async def callback_admin_server_activate(callback: CallbackQuery):
    """Активация сервера."""
    if not is_admin(callback.from_user.id):
        return
    
    server_id = int(callback.data.split("_")[3])
    
    await queries.set_server_active(server_id, True)
    
    # Сбрасываем кэш
    await queries.invalidate_cache()
    
    await callback.answer("✅ Сервер активирован", show_alert=True)
    
    # Обновляем сообщение
    await admin_servers(callback.message, None)


@router.callback_query(F.data.startswith("admin_server_deactivate_"))
async def callback_admin_server_deactivate(callback: CallbackQuery):
    """Деактивация сервера."""
    if not is_admin(callback.from_user.id):
        return
    
    server_id = int(callback.data.split("_")[3])
    
    await queries.set_server_active(server_id, False)
    
    # Сбрасываем кэш
    await queries.invalidate_cache()
    
    await callback.answer("❌ Сервер деактивирован", show_alert=True)
    
    # Обновляем сообщение
    await admin_servers(callback.message, None)


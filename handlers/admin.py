"""
Обработчики админ-панели FreakVPN.
Все функции управления ботом для администраторов.
Обновлено по ТЗ v2.
"""

import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
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
    get_users_list_keyboard,
    get_admin_balance_confirm_keyboard,
    get_admin_servers_keyboard,
    get_server_actions_keyboard,
    get_admin_mailing_keyboard,
    get_admin_settings_keyboard,
    get_admin_tariffs_keyboard,
    get_admin_cancel_keyboard,
    get_admin_back_keyboard,
    get_admin_withdraw_confirm_keyboard,
    get_admin_logs_keyboard,
    get_admin_promocodes_keyboard,
    get_admin_promo_type_keyboard,
    get_admin_search_again_keyboard,
    get_admin_other_keyboard,
    get_server_delete_confirm_keyboard,
    get_promo_delete_confirm_keyboard,
    get_key_delete_confirm_keyboard,
    get_user_block_confirm_keyboard,
    # Новые клавиатуры по ТЗ
    get_admin_users_menu_keyboard,
    get_admin_user_search_keyboard,
    get_admin_users_list_keyboard,
    get_admin_user_card_keyboard,
    get_admin_stats_keyboard,
    get_admin_servers_list_keyboard,
    get_admin_server_card_keyboard,
    get_admin_other_menu_keyboard,
    get_admin_logs_menu_keyboard,
    get_admin_logs_view_keyboard,
    get_admin_promocodes_list_keyboard,
    get_admin_promo_card_keyboard,
    get_admin_settings_menu_keyboard,
    get_admin_mailing_audience_keyboard,
    get_admin_mailing_preview_keyboard,
    get_admin_mailing_progress_keyboard,
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
from utils.helpers import format_balance, format_date, format_datetime, mask_key, parse_datetime, get_country_flag, get_days_left
from services.xui_api import XuiService, check_server_connection

router = Router()


# ================== СОСТОЯНИЯ FSM ==================

class AdminStates(StatesGroup):
    """Состояния для админ-операций."""
    
    # Пользователи
    search_user = State()
    add_balance_amount = State()
    withdraw_balance_amount = State()
    extend_days = State()
    
    # Серверы (пошаговое добавление)
    add_server_name = State()
    add_server_country = State()
    add_server_domain = State()
    add_server_ip = State()
    add_server_port = State()
    add_server_login = State()
    add_server_password = State()
    add_server_confirm = State()
    edit_server = State()
    
    # Рассылка
    mailing_content = State()
    
    # Настройки
    edit_tariff_price = State()
    edit_trial_days = State()
    edit_contacts = State()
    edit_payment_details = State()

    # Промокоды
    create_promo_code = State()
    create_promo_type = State()
    create_promo_value = State()
    create_promo_max_uses = State()
    create_promo_expires = State()


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
        "👥 Управление пользователями",
        reply_markup=get_admin_users_menu_keyboard()
    )


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
            reply_markup=get_admin_cancel_keyboard()
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
    
    # Формируем информацию - упрощенный статус
    expires_dt = parse_datetime(user.get("expires_at"))
    if user.get("status") == "blocked":
        status = "🚫 Заблокирован"
    elif expires_dt and expires_dt > datetime.utcnow():
        status = "💎 Статус: Активен"
    else:
        status = "💎 Статус: Не активна"
    
    key_preview = mask_key(user.get("current_key", "Нет"))
    
    is_blocked = user.get("status") == "blocked"
    
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
        reply_markup=get_user_actions_keyboard(user["user_id"], is_blocked=is_blocked)
    )

    await state.clear()
    

# ================== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ==================

@router.message(F.text == "📋 Список пользователей")
async def admin_users_list(message: Message, state: FSMContext):
    """Показ списка пользователей с пагинацией."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    users = await queries.get_all_users()
    
    if not users:
        await message.answer(
            "👥 Пользователей пока нет",
            reply_markup=get_admin_users_menu_keyboard()
        )
        return
    
    # Показываем первую страницу (8 пользователей по ТЗ)
    keyboard = get_users_list_keyboard(users, page=0, per_page=8)
    
    await message.answer(
        f"👥 Список пользователей (всего: {len(users)})",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("admin_users_page_"))
async def callback_admin_users_page(callback: CallbackQuery):
    """Пагинация списка пользователей."""
    if not is_admin(callback.from_user.id):
        return
    
    page = int(callback.data.split("_")[3])
    users = await queries.get_all_users()
    
    keyboard = get_admin_users_list_keyboard(users, page=page, per_page=8)
    
    await callback.message.edit_text(
        f"👥 Управление пользователями (всего: {len(users)})",
        reply_markup=keyboard
    )
    
    await callback.answer()


@router.callback_query(F.data == "admin_user_search")
async def callback_admin_user_search(callback: CallbackQuery, state: FSMContext):
    """Поиск пользователя из меню."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.set_state(AdminStates.search_user)
    
    await callback.message.edit_text(
        "🔍 Введи ID или @username пользователя для поиска:",
        reply_markup=get_admin_user_search_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users_list")
async def callback_admin_users_list(callback: CallbackQuery, state: FSMContext):
    """Список пользователей из меню."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    users = await queries.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "👥 Пользователей пока нет",
            reply_markup=get_admin_users_menu_keyboard()
        )
        return
    
    keyboard = get_users_list_keyboard(users, page=0, per_page=8)
    await callback.message.edit_text(
        f"👥 Список пользователей (всего: {len(users)})",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_"))
async def callback_admin_user_details(callback: CallbackQuery):
    """Просмотр информации о пользователе из списка."""
    if not is_admin(callback.from_user.id):
        return
    
    # Пропускаем специальные callback data
    if callback.data in ["admin_user_search", "admin_users_list"]:
        return
    
    try:
        user_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    user = await queries.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Формируем информацию
    server_name = "Не выбран"
    if user.get("server_id"):
        server = await queries.get_server(user["server_id"])
        if server:
            server_name = server["name"]
    
    expires_dt = parse_datetime(user.get("expires_at"))
    if user.get("status") == "blocked":
        status = "🚫 Заблокирован"
    elif expires_dt and expires_dt > datetime.utcnow():
        status = "💎 Активен"
    else:
        status = "💎 Не активна"
    
    key_preview = mask_key(user.get("current_key", "Нет"))
    is_blocked = user.get("status") == "blocked"
    
    await callback.message.edit_text(
        ADMIN_USER_INFO.format(
            username=f"@{user['username']}" if user.get("username") else "Нет username",
            user_id=user["user_id"],
            registered_at=format_date(user.get("registered_at")),
            status=status,
            server=server_name,
            balance=format_balance(user.get("balance", 0)),
            key_preview=key_preview
        ),
        reply_markup=get_user_actions_keyboard(user["user_id"], is_blocked=is_blocked)
    )
    
    await callback.answer()


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
    
    # Проверяем формат callback data
    parts = callback.data.split("_")
    if len(parts) < 5 or parts[3] == "server":
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return
    
    try:
        amount = int(parts[3])
        target_user_id = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return
    
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
    """Блокировка/разблокировка пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[2])
    admin_id = callback.from_user.id
    
    # Проверяем, не является ли пользователь админом
    if user_id in config.ADMIN_IDS:
        await callback.answer(
            "❌ Нельзя заблокировать администратора!",
            show_alert=True
        )
        return
    
    user = await queries.get_user(user_id)
    
    if user.get("status") == "blocked":
        # Разблокируем
        await queries.set_user_status(user_id, "active")
        
        # Логируем
        await queries.add_log(
            category="admin",
            action="user_unblocked",
            user_id=admin_id,
            target_user_id=user_id
        )
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                user_id,
                "✅ Твой доступ к StarinaVPN восстановлен!\n\n"
                "Ты снова можешь пользоваться сервисом."
            )
        except Exception:
            pass
        
        await callback.answer("✅ Пользователь разблокирован", show_alert=True)
        
        # Обновляем кнопки (теперь is_blocked=False)
        await callback.message.edit_reply_markup(
            reply_markup=get_user_actions_keyboard(user_id, is_blocked=False)
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
        
        # Логируем
        await queries.add_log(
            category="admin",
            action="user_blocked",
            user_id=admin_id,
            target_user_id=user_id
        )
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                user_id,
                "🚫 Твой доступ к StarinaVPN заблокирован.\n\n"
                "Для восстановления доступа обратитесь к администратору: @StarinaVPN_Support"
            )
        except Exception:
            pass
        
        await callback.answer("✅ Пользователь заблокирован", show_alert=True)
        
        # Обновляем кнопки (теперь is_blocked=True)
        await callback.message.edit_reply_markup(
            reply_markup=get_user_actions_keyboard(user_id, is_blocked=True)
        )
    
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
    
    # Статистика по серверам с нагрузкой
    servers_stats = await queries.get_servers_with_load()
    
    servers_text = ""
    for stat in servers_stats:
        flag = get_country_flag(stat["country_code"])
        status = "ON" if stat["is_active"] else "OFF"
        load = stat.get("load", 0)
        capacity = stat.get("capacity", 200) or 200
        load_percent = int(load / capacity * 100) if capacity > 0 else 0
        servers_text += f"{flag} {stat['name']}: {stat.get('users_count', 0)} польз., нагрузка {load_percent}%\n"
    
    await message.answer(
        f"📊 Статистика\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Активных сегодня: {active_today}\n"
        f"🆕 Новых за сегодня: {new_today}\n\n"
        f"💰 Общий баланс: {format_balance(total_balance)} RUB\n"
        f"💵 Продажи за месяц: {format_balance(month_sales)} RUB\n"
        f"📊 Средний чек: {format_balance(avg_check)} RUB\n\n"
        f"🌍 По серверам:\n{servers_text or 'Нет серверов'}",
        reply_markup=get_admin_stats_keyboard()
    )
    

# ================== РАЗДЕЛ СЕРВЕРЫ ==================

@router.message(F.text == "🌍 Серверы")
async def admin_servers(message: Message, state: FSMContext):
    """Управление серверами."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    servers = await queries.get_servers_with_load()
    
    text = "🌍 Управление серверами\n\n"
    
    if servers:
        for s in servers:
            status = "ON" if s.get("is_active") else "OFF"
            flag = get_country_flag(s.get("country_code", ""))
            users = s.get("users_count", 0)
            capacity = s.get("capacity", 200) or 200
            load = int(users / capacity * 100) if capacity > 0 else 0
            text += f"{flag} {s['name']} - {users} польз. - нагрузка {load}%\n"
    
    await message.answer(text, reply_markup=get_admin_servers_list_keyboard(servers))


@router.callback_query(F.data == "admin_add_server")
async def callback_admin_add_server(callback: CallbackQuery, state: FSMContext):
    """Начало пошагового добавления сервера - шаг 1: название."""
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "➕ Добавление сервера (шаг 1/7)\n\n"
        "Введи название сервера (например: Амстердам):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_server_name)
    await callback.answer()


@router.message(AdminStates.add_server_name)
async def admin_add_server_name(message: Message, state: FSMContext):
    """Шаг 2: страна."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    name = message.text.strip()
    if not name or len(name) > 50:
        await message.answer("❌ Неверное название. Попробуй ещё раз:")
        return
    
    await state.update_data(server_name=name)
    
    await message.answer(
        "➕ Добавление сервера (шаг 2/7)\n\n"
        "Введи код страны (2 буквы, например: NL, DE, US, RU):",
        reply_markup=get_admin_cancel_keyboard()
    )

    await state.set_state(AdminStates.add_server_country)


@router.message(AdminStates.add_server_country)
async def admin_add_server_country(message: Message, state: FSMContext):
    """Шаг 3: домен."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    country = message.text.strip().upper()
    if len(country) != 2:
        await message.answer("❌ Неверный код страны. Введи 2 буквы (например: NL):")
        return
    
    await state.update_data(server_country=country)
    
    await message.answer(
        "➕ Добавление сервера (шаг 3/7)\n\n"
        "Введи домен (например: ams.freakvpn.ru):",
        reply_markup=get_admin_cancel_keyboard()
    )

    await state.set_state(AdminStates.add_server_domain)


@router.message(AdminStates.add_server_domain)
async def admin_add_server_domain(message: Message, state: FSMContext):
    """Шаг 4: IP адрес."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    domain = message.text.strip().lower()
    if not domain or "." not in domain:
        await message.answer("❌ Неверный домен. Попробуй ещё раз:")
        return
    
    await state.update_data(server_domain=domain)
    
    await message.answer(
        "➕ Добавление сервера (шаг 4/7)\n\n"
        "Введи IP адрес сервера (например: 45.67.89.10):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_server_ip)


@router.message(AdminStates.add_server_ip)
async def admin_add_server_ip(message: Message, state: FSMContext):
    """Шаг 5: порт."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    ip = message.text.strip()
    import re
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        await message.answer("❌ Неверный IP адрес. Попробуй ещё раз:")
        return
    
    await state.update_data(server_ip=ip)
    
    await message.answer(
        "➕ Добавление сервера (шаг 5/7)\n\n"
        "Введи порт X-UI (обычно 54321 или 2053):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_server_port)


@router.message(AdminStates.add_server_port)
async def admin_add_server_port(message: Message, state: FSMContext):
    """Шаг 6: логин."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        port = int(message.text.strip())
        if port <= 0 or port > 65535:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверный порт. Введи число от 1 до 65535:")
        return
    
    await state.update_data(server_port=port)
    
    await message.answer(
        "➕ Добавление сервера (шаг 6/7)\n\n"
        "Введи логин от X-UI:",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_server_login)


@router.message(AdminStates.add_server_login)
async def admin_add_server_login(message: Message, state: FSMContext):
    """Шаг 7: пароль."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    login = message.text.strip()
    if not login:
        await message.answer("❌ Логин не может быть пустым. Попробуй ещё раз:")
        return
    
    await state.update_data(server_login=login)
    
    await message.answer(
        "➕ Добавление сервера (шаг 7/7)\n\n"
        "Введи пароль от X-UI:",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.add_server_password)


@router.message(AdminStates.add_server_password)
async def admin_add_server_password(message: Message, state: FSMContext):
    """Подтверждение и проверка подключения."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    password = message.text.strip()
    if not password:
        await message.answer("❌ Пароль не может быть пустым. Попробуй ещё раз:")
        return
    
    data = await state.get_data()
    
    # Формируем API URL
    api_url = f"https://{data['server_ip']}:{data['server_port']}"
    
    # Сохраняем все данные
    await state.update_data(
        server_password=password,
        server_api_url=api_url
    )
    
    # Формируем текст подтверждения
    confirm_text = (
        "📋 Проверь данные и подтверди:\n\n"
        f"Название: {data['server_name']}\n"
        f"Страна: {data['server_country']}\n"
        f"Домен: {data['server_domain']}\n"
        f"IP: {data['server_ip']}\n"
        f"Порт: {data['server_port']}\n"
        f"Логин: {data['server_login']}\n"
        f"Пароль: ••••••••\n\n"
        "Подтвердить добавление?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin_server_save"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"),
        ]
    ])
    
    await message.answer(confirm_text, reply_markup=keyboard)
    
    await state.set_state(AdminStates.add_server_confirm)


@router.callback_query(F.data == "admin_server_save")
async def callback_admin_server_save(callback: CallbackQuery, state: FSMContext):
    """Подтверждение добавления сервера с проверкой подключения."""
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    
    # Проверяем подключение перед сохранением
    await callback.message.edit_text("🔄 Проверка подключения к серверу...")
    
    server_check = {
        "api_url": data["server_api_url"],
        "api_username": data["server_login"],
        "api_password": data["server_password"]
    }
    
    is_connected = await check_server_connection(server_check)
    
    if not is_connected:
        await callback.message.edit_text(
            "❌ Не удалось подключиться к X-UI панели.\n\n"
            "Проверь данные и попробуй снова.",
            reply_markup=get_admin_cancel_keyboard()
        )
        await state.clear()
        return
    
    # Добавляем сервер в БД
    server_id = await queries.create_server(
        name=data["server_name"],
        country_code=data["server_country"],
        domain=data["server_domain"],
        ip=data["server_ip"],
        api_url=data["server_api_url"],
        api_username=data["server_login"],
        api_password=data["server_password"],
        port=443,
        inbound_id=1
    )
    
    await callback.message.edit_text(
        f"✅ Сервер успешно добавлен!\n\n"
        f"ID: {server_id}\n"
        f"Название: {data['server_name']}\n"
        f"Домен: {data['server_domain']}\n"
        f"Статус: ✅ Подключен",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()
    
    logger.info(f"Админ добавил сервер: {data['server_name']} ({data['server_domain']})")


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

@router.message(F.text == "📨 Рассылка")
async def admin_mailing(message: Message, state: FSMContext):
    """Создание рассылки."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    # Собираем статистику по аудиториям
    all_users = await queries.get_users_count()
    active_keys = await db.fetchval("SELECT COUNT(*) FROM user_keys WHERE is_active = 1") or 0
    has_balance = await db.fetchval("SELECT COUNT(*) FROM users WHERE balance > 0") or 0
    no_promo = all_users
    expiring = len(await queries.get_expiring_keys(hours=72))
    autorenew = await db.fetchval("SELECT COUNT(*) FROM user_keys WHERE auto_renew = 1 AND is_active = 1") or 0
    
    audience_stats = {
        "all": all_users,
        "active_keys": active_keys,
        "has_balance": has_balance,
        "no_promo": no_promo,
        "expiring": expiring,
        "autorenew": autorenew,
    }
    
    await message.answer(
        "📨 Выбери аудиторию для рассылки:",
        reply_markup=get_admin_mailing_keyboard(all_users)
    )


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
    
    tariffs = await queries.get_tariffs()
    trial_days = await queries.get_setting_int("trial_days", 3)
    min_topup = await queries.get_min_topup()
    
    await message.answer(
        "⚙️ Настройки",
        reply_markup=get_admin_settings_keyboard()
    )


# ================== ПРОЧЕЕ ==================

@router.message(F.text == "⚙️ Прочее")
async def admin_other(message: Message, state: FSMContext):
    """Раздел 'Прочее'."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    await message.answer(
        "⚙️ Дополнительные настройки",
        reply_markup=get_admin_other_keyboard()
    )


# ================== НАВИГАЦИЯ ==================

@router.callback_query(F.data == "admin_main")
async def callback_admin_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админ-панели."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()

    await callback.message.edit_text(
        "🔐 Панель управления\n\n"
        "Выбери раздел:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_other")
async def callback_admin_other(callback: CallbackQuery, state: FSMContext):
    """Возврат в раздел 'Прочее'."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    
    await callback.message.edit_text(
        "⚙️ Дополнительные настройки\n\n"
        "Выбери раздел:",
        reply_markup=get_admin_other_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "close_message")
async def callback_close_message(callback: CallbackQuery):
    """Закрытие сообщения."""
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text("❌ Сообщение закрыто")
    await callback.answer()


@router.callback_query(F.data == "admin_cancel")
async def callback_admin_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена действия и возврат в главное меню."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    
    await callback.message.edit_text(
        "🔐 Панель управления\n\n"
        "Выбери раздел:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


# ================== ПРОЧЕЕ - ОБРАБОТЧИКИ ==================

@router.callback_query(F.data == "admin_tariffs")
async def callback_admin_tariffs(callback: CallbackQuery):
    """Просмотр тарифов."""
    if not is_admin(callback.from_user.id):
        return
    
    tariffs = await queries.get_tariffs()
    
    text = "💰 Тарифы\n\n"
    for t in tariffs:
        price = t["price"] // 100
        text += f"• {t['name']}: {price} ₽\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payment_details")
async def callback_admin_payment_details(callback: CallbackQuery):
    """Просмотр реквизитов."""
    if not is_admin(callback.from_user.id):
        return
    
    # Получаем настройки реквизитов
    payment_method = await queries.get_setting("payment_method") or "QIWI"
    qiwi_number = await queries.get_setting("qiwi_number") or "не настроено"
    crypto_wallet = await queries.get_setting("crypto_wallet") or "не настроено"
    card_number = await queries.get_setting("card_number") or "не настроено"
    
    await callback.message.edit_text(
        "📝 Реквизиты для оплаты\n\n"
        f"Способ: {payment_method}\n"
        f"QIWI: {qiwi_number}\n"
        f"Карта: {card_number}\n"
        f"Crypto: {crypto_wallet}",
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_contacts")
async def callback_admin_contacts(callback: CallbackQuery):
    """Просмотр контактов."""
    if not is_admin(callback.from_user.id):
        return
    
    support = await queries.get_setting("support_contact") or "@StarinaVPN_Support_bot"
    payment = await queries.get_setting("payment_contact") or "@StarinaVPN_Shop"
    news = await queries.get_setting("news_channel") or "@StarinaVPN_News"
    
    await callback.message.edit_text(
        "📞 Контакты\n\n"
        f"• Поддержка: {support}\n"
        f"• Оплата: {payment}\n"
        f"• Новости: {news}",
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_servers")
async def callback_admin_servers(callback: CallbackQuery):
    """Просмотр списка серверов."""
    if not is_admin(callback.from_user.id):
        return
    
    servers = await queries.get_servers()
    
    text = "🌍 Серверы\n\n"
    for s in servers:
        status = "✅" if s.get("is_active") else "❌"
        text += f"{status} {s['name']}\n"
    
    if not servers:
        text = "🌍 Серверы\n\nНет серверов"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_trial_settings")
async def callback_admin_trial_settings(callback: CallbackQuery):
    """Просмотр настроек пробного периода."""
    if not is_admin(callback.from_user.id):
        return
    
    trial_days = await queries.get_setting("trial_days") or "3"
    
    await callback.message.edit_text(
        "🎁 Пробный период\n\n"
        f"Текущее значение: {trial_days} дней",
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_referral_settings")
async def callback_admin_referral_settings(callback: CallbackQuery):
    """Просмотр настроек реферальной системы."""
    if not is_admin(callback.from_user.id):
        return
    
    referral_bonus_percent = await queries.get_setting_int("referral_bonus_percent", 15)
    referral_min_topup = await queries.get_setting_int("referral_min_topup", 100)
    
    await callback.message.edit_text(
        "👥 Реферальная система\n\n"
        f"Бонус: {referral_bonus_percent}%\n"
        f"Минимальное пополнение: {referral_min_topup} ₽",
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_min_topup")
async def callback_admin_min_topup(callback: CallbackQuery):
    """Просмотр минимальной суммы пополнения."""
    if not is_admin(callback.from_user.id):
        return
    
    min_topup = await queries.get_setting_int("min_topup", 50)
    
    await callback.message.edit_text(
        "💸 Минимальная сумма пополнения\n\n"
        f"Текущее значение: {min_topup} ₽",
        reply_markup=get_admin_back_keyboard("admin_other")
    )
    await callback.answer()


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
    """Обработка новой цены тарифа с подтверждением."""
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
    tariff = await queries.get_tariff(tariff_id)
    
    old_price = tariff["price"] // 100 if tariff else 0
    new_price = price_kopecks // 100
    
    # Показываем подтверждение
    await message.answer(
        f"📋 Подтверди изменение цены тарифа:\n\n"
        f"Тариф: {tariff['name']}\n"
        f"Старая цена: {old_price} ₽\n"
        f"Новая цена: {new_price} ₽\n\n"
        f"Подтвердить изменение?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Подтвердить ({new_price} ₽)",
                    callback_data=f"admin_confirm_tariff_price_{tariff_id}_{price_kopecks}"
                ),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"),
            ]
        ])
    )


@router.callback_query(F.data.startswith("admin_confirm_tariff_price_"))
async def callback_admin_confirm_tariff_price(callback: CallbackQuery, state: FSMContext):
    """Подтверждение изменения цены тарифа."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split("_")
    tariff_id = int(parts[4])
    price_kopecks = int(parts[5])
    
    await queries.update_tariff_price(tariff_id, price_kopecks)
    
    tariff = await queries.get_tariff(tariff_id)
    
    await callback.message.edit_text(
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
    
    support = await queries.get_setting("support_contact") or "@ShadowRing"
    payment = await queries.get_setting("payment_contact") or "@ShadowRing"
    
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


# ================== СПИСАНИЕ БАЛАНСА ==================

@router.callback_query(F.data.startswith("admin_withdraw_balance_"))
async def callback_admin_withdraw_balance(callback: CallbackQuery, state: FSMContext):
    """Начало списания баланса."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[3])
    await state.update_data(target_user_id=user_id)
    
    user = await queries.get_user(user_id)
    
    await callback.message.edit_text(
        f"💰 Списание баланса\n\n"
        f"ID: {user_id}\n"
        f"@{user['username'] if user.get('username') else 'Нет username'}\n"
        f"Текущий баланс: {format_balance(user.get('balance', 0))} ₽\n\n"
        f"Введи сумму для списания (в рублях):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.withdraw_balance_amount)
    await callback.answer()


@router.message(AdminStates.withdraw_balance_amount)
async def admin_process_withdraw_amount(message: Message, state: FSMContext):
    """Обработка суммы списания."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
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
    
    if amount_kopecks > current_balance:
        await message.answer(
            f"❌ Недостаточно средств на балансе!\n\n"
            f"Текущий баланс: {format_balance(current_balance)} ₽\n"
            f"Сумма списания: {format_balance(amount_kopecks)} ₽\n\n"
            f"Введи меньшую сумму:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    new_balance = current_balance - amount_kopecks
    await state.update_data(amount=amount_kopecks)
    
    await message.answer(
        f"Списать {format_balance(amount_kopecks)} ₽ с баланса пользователя?\n\n"
        f"@{user['username'] if user.get('username') else 'ID: ' + str(target_user_id)}\n"
        f"Текущий баланс: {format_balance(current_balance)} ₽\n"
        f"Новый баланс: {format_balance(new_balance)} ₽",
        reply_markup=get_admin_withdraw_confirm_keyboard(amount_kopecks, target_user_id)
    )


@router.callback_query(F.data.startswith("admin_confirm_withdraw_"))
async def callback_admin_confirm_withdraw(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение списания баланса."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split("_")
    amount = int(parts[3])
    target_user_id = int(parts[4])
    
    admin_id = callback.from_user.id
    
    # Списываем баланс
    new_balance = await queries.update_user_balance(target_user_id, -amount)
    
    # Создаем транзакцию
    await queries.create_transaction(
        user_id=target_user_id,
        amount=-amount,
        transaction_type="admin_withdraw",
        description="Списание администратором",
        admin_id=admin_id
    )
    
    # Добавляем запись в логи
    await queries.add_log(
        category="payment",
        action="withdraw",
        user_id=admin_id,
        target_user_id=target_user_id,
        amount=amount,
        details={"reason": "admin_correction"}
    )
    
    # Сообщение админу
    await callback.message.edit_text(
        f"✅ Баланс пользователя уменьшен на {format_balance(amount)} ₽\n"
        f"Новый баланс: {format_balance(new_balance)} ₽"
    )
    
    # Уведомление пользователю
    try:
        await bot.send_message(
            target_user_id,
            f"💰 Списание с баланса!\n\n"
            f"Списано: {format_balance(amount)} ₽\n"
            f"Текущий баланс: {format_balance(new_balance)} ₽\n\n"
            f"Причина: корректировка администратора.\n"
            f"По вопросам: @StarinaVPN_Support"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {target_user_id}: {e}")
    
    await state.clear()
    await callback.answer("✅ Баланс списан")
    
    logger.info(
        f"Админ списал баланс: admin={admin_id}, user={target_user_id}, amount={amount}"
    )


# ================== ЛОГИ ==================

@router.message(F.text == "📋 Логи")
async def admin_logs(message: Message, state: FSMContext):
    """Показ панели логов."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    await message.answer(
        "📋 Выбери категорию логов:",
        reply_markup=get_admin_logs_menu_keyboard()
    )


@router.callback_query(F.data.startswith("admin_logs_"))
async def callback_admin_logs(callback: CallbackQuery, state: FSMContext):
    """Показ логов по категории."""
    if not is_admin(callback.from_user.id):
        return
    
    category = callback.data.split("_")[2]
    
    if category == "clean":
        deleted = await queries.delete_old_logs(30)
        await callback.answer(f"🗑 Удалено {deleted} старых логов", show_alert=True)
        # Обновляем список
        categories = await queries.get_log_categories()
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_logs_keyboard(categories)
        )
        return
    
    logs = await queries.get_logs(category=category, limit=50)
    
    if not logs:
        await callback.answer("📋 Нет записей в этой категории", show_alert=True)
        return
    
    text = f"📋 Логи: {category}\n\n"
    for log in logs[:20]:
        text += f"🕒 {format_datetime(log['created_at'])}\n"
        text += f"   {log['action']}"
        if log.get('amount'):
            text += f" | {format_balance(log['amount'])} ₽"
        if log.get('user_id'):
            text += f" | user_id: {log['user_id']}"
        text += "\n\n"
    
    if len(logs) > 20:
        text += f"... и еще {len(logs) - 20} записей"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard("admin_logs_back")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_logs_back")
async def callback_admin_logs_back(callback: CallbackQuery, state: FSMContext):
    """Возврат к списку категорий логов."""
    if not is_admin(callback.from_user.id):
        return
    
    categories = await queries.get_log_categories()
    await callback.message.edit_text(
        "📋 Панель логов\n\n"
        "Выбери категорию для просмотра:",
        reply_markup=get_admin_logs_keyboard(categories)
    )
    await callback.answer()


# ================== ПРОМОКОДЫ ==================

@router.message(F.text == "🎫 Промокоды")
async def admin_promocodes(message: Message, state: FSMContext):
    """Управление промокодами."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()

    promocodes = await queries.get_all_promocodes()

    text = "🎫 Управление промокодами (всего: {})\n\n".format(len(promocodes))
    
    if promocodes:
        for p in promocodes:
            status = "ON" if p["is_active"] else "OFF"
            promo_type = p.get("type", "")
            
            # Форматируем тип
            if promo_type == "discount_percent":
                type_text = f"скидка {p.get('value', 0)}%"
            elif promo_type == "discount_fixed":
                type_text = f"{p.get('value', 0) // 100}RUB"
            elif promo_type == "free_days":
                type_text = f"{p.get('value', 0)} дней"
            elif promo_type == "balance":
                type_text = f"{p.get('value', 0) // 100}RUB баланс"
            else:
                type_text = promo_type
            
            used = p.get("used_count", 0)
            max_uses = p.get("max_uses", 0)
            limit_text = f"{used}/{max_uses}" if max_uses > 0 else f"{used}/inf"
            
            expires = p.get("expires_at")
            if expires:
                try:
                    expires_text = format_date(expires)
                except:
                    expires_text = "бессрочно"
            else:
                expires_text = "бессрочно"
            
            text += f"{status} {p['code']} - {type_text} - {limit_text} - до {expires_text}\n"
    else:
        text += "Промокодов пока нет."
    
    await message.answer(
        text,
        reply_markup=get_admin_promocodes_keyboard(promocodes)
    )
    

@router.callback_query(F.data == "admin_create_promo")
async def callback_admin_create_promo(callback: CallbackQuery, state: FSMContext):
    """Начало создания промокода."""
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "🎫 Создание промокода\n\n"
        "Введи код промокода (латиница, цифры, до 20 символов):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.create_promo_code)
    await callback.answer()


@router.message(AdminStates.create_promo_code)
async def admin_create_promo_code(message: Message, state: FSMContext):
    """Обработка ввода кода промокода."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    code = message.text.strip().upper()
    
    if len(code) > 20 or not code.isalnum():
        await message.answer(
            "❌ Код должен содержать только латиницу и цифры, до 20 символов.\n"
            "Введи другой код:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    existing = await queries.get_promocode(code)
    if existing:
        await message.answer(
            "❌ Промокод с таким кодом уже существует.\n"
            "Введи другой код:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    await state.update_data(promo_code=code)
    
    await message.answer(
        "Выбери тип промокода:",
        reply_markup=get_admin_promo_type_keyboard()
    )
    
    await state.set_state(AdminStates.create_promo_type)


@router.callback_query(AdminStates.create_promo_type, F.data.startswith("promo_type_"))
async def admin_create_promo_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа промокода."""
    if not is_admin(callback.from_user.id):
        return
    
    promo_type = callback.data.split("_")[2]
    
    type_names = {
        "discount_percent": "скидка в %",
        "discount_fixed": "скидка в ₽",
        "free_days": "бесплатные дни",
        "balance": "начисление на баланс",
        "subscription_extension": "продление подписки"
    }
    
    await state.update_data(promo_type=promo_type)
    
    await callback.message.edit_text(
        f"🎫 Тип: {type_names.get(promo_type, promo_type)}\n\n"
        f"Введи значение:\n"
        f"• Для % скидки: число от 1 до 99\n"
        f"• Для ₽ скидки: сумма в рублях\n"
        f"• Для дней: количество дней\n"
        f"• Для баланса: сумма в рублях",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.create_promo_value)
    await callback.answer()


@router.message(AdminStates.create_promo_value)
async def admin_create_promo_value(message: Message, state: FSMContext):
    """Обработка ввода значения промокода."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    data = await state.get_data()
    promo_type = data["promo_type"]
    
    try:
        value = int(message.text.strip())
        
        if promo_type == "discount_percent" and not (1 <= value <= 99):
            raise ValueError()
        if promo_type in ["discount_fixed", "balance"] and value <= 0:
            raise ValueError()
        if promo_type in ["free_days", "subscription_extension"] and value <= 0:
            raise ValueError()
            
    except ValueError:
        await message.answer(
            "❌ Неверное значение. Попробуй еще раз:",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    # Конвертация в копейки для денежных типов
    if promo_type in ["discount_fixed", "balance"]:
        value = value * 100  # рубли -> копейки
    
    await state.update_data(promo_value=value)
    
    await message.answer(
        "Введи максимальное количество использований (0 = безлимит):",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.create_promo_max_uses)


@router.message(AdminStates.create_promo_max_uses)
async def admin_create_promo_max_uses(message: Message, state: FSMContext):
    """Обработка ввода лимита использований."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        max_uses = int(message.text.strip())
        if max_uses < 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            "❌ Неверное значение. Введи число (0 = безлимит):",
            reply_markup=get_admin_cancel_keyboard()
        )
        return
    
    await state.update_data(promo_max_uses=max_uses)
    
    await message.answer(
        "Введи дату истечения (в формате ДД.ММ.ГГГГ ЧЧ:ММ)\n"
        "или 0 если промокод бессрочный:",
        reply_markup=get_admin_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.create_promo_expires)


@router.message(AdminStates.create_promo_expires)
async def admin_create_promo_expires(message: Message, state: FSMContext):
    """Обработка ввода даты истечения."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    expires_at = None
    text = message.text.strip()
    
    if text != "0":
        try:
            expires_at = datetime.strptime(text, "%d.%m.%Y %H:%M")
        except ValueError:
            await message.answer(
                "❌ Неверный формат даты.\n"
                "Используй формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "или 0 для бессрочного:",
                reply_markup=get_admin_cancel_keyboard()
            )
            return
    
    data = await state.get_data()
    
    # Создаем промокод
    await queries.create_promocode(
        code=data["promo_code"],
        type=data["promo_type"],
        value=data["promo_value"],
        max_uses=data["promo_max_uses"],
        expires_at=expires_at,
        created_by=message.from_user.id
    )
    
    # Логируем
    await queries.add_log(
        category="promocode",
        action="created",
        user_id=message.from_user.id,
        details={
            "code": data["promo_code"],
            "type": data["promo_type"],
            "value": data["promo_value"],
            "max_uses": data["promo_max_uses"],
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    )
    
    # Формируем отображаемое значение (в рублях для денежных типов)
    display_value = data["promo_value"]
    if data["promo_type"] in ["discount_fixed", "balance"]:
        display_value = data["promo_value"] // 100  # копейки -> рубли для отображения
    
    type_names = {
        "discount_percent": f"Скидка {display_value}%",
        "discount_fixed": f"Скидка {display_value} ₽",
        "free_days": f"{display_value} бесплатных дней",
        "balance": f"Начисление {display_value} ₽ на баланс",
        "subscription_extension": f"Продление на {display_value} дней"
    }
    
    await message.answer(
        f"✅ Промокод создан!\n\n"
        f"Код: {data['promo_code']}\n"
        f"Тип: {type_names.get(data['promo_type'], data['promo_type'])}\n"
        f"Лимит: {data['promo_max_uses'] or '∞'}\n"
        f"Истекает: {format_date(expires_at) if expires_at else 'бессрочно'}",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()


# ================== ПОВТОРНЫЙ ПОИСК ==================

@router.callback_query(F.data == "admin_search_again")
async def callback_admin_search_again(callback: CallbackQuery, state: FSMContext):
    """Повторный поиск пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.delete()
    
    await callback.message.answer(
        "🔍 Введи ID или @username пользователя для поиска:",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AdminStates.search_user)
    await callback.answer()


# ================== ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ==================

@router.callback_query(F.data.startswith("admin_server_delete_"))
async def callback_admin_server_delete_confirm(callback: CallbackQuery):
    """Запрос подтверждения удаления сервера."""
    if not is_admin(callback.from_user.id):
        return
    
    server_id = int(callback.data.split("_")[4])
    await callback.message.edit_text(
        "⚠️ Ты точно хочешь удалить этот сервер?",
        reply_markup=get_server_delete_confirm_keyboard(server_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_server_"))
async def callback_admin_confirm_delete_server(callback: CallbackQuery):
    """Подтверждение удаления сервера."""
    if not is_admin(callback.from_user.id):
        return
    
    server_id = int(callback.data.split("_")[4])
    
    try:
        # Получаем сервер
        server = await queries.get_server(server_id)
        if not server:
            await callback.answer("❌ Сервер не найден", show_alert=True)
            return
        
        # Деактивируем сервер (мягкое удаление)
        await queries.set_server_active(server_id, False)
        
        await queries.add_log(
            category="server",
            action="deleted",
            user_id=callback.from_user.id,
            details={"server_id": server_id, "server_name": server["name"]}
        )
        
        await callback.message.edit_text(
            f"✅ Сервер '{server['name']}' удален.",
            reply_markup=get_admin_back_keyboard("admin_servers")
        )
        logger.info(f"Удален сервер: {server['name']} (id={server_id})")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении сервера: {e}")
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_promo_delete_"))
async def callback_admin_promo_delete_confirm(callback: CallbackQuery):
    """Запрос подтверждения удаления промокода."""
    if not is_admin(callback.from_user.id):
        return
    
    promo_id = int(callback.data.split("_")[3])
    await callback.message.edit_text(
        "⚠️ Ты точно хочешь удалить этот промокод навсегда?",
        reply_markup=get_promo_delete_confirm_keyboard(promo_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_promo_"))
async def callback_admin_confirm_delete_promo(callback: CallbackQuery):
    """Подтверждение удаления промокода."""
    if not is_admin(callback.from_user.id):
        return
    
    promo_id = int(callback.data.split("_")[4])
    
    try:
        # Получаем промокод для логов
        from database.queries import get_promocode
        # Удаляем промокод из БД
        await queries.db.execute(
            "DELETE FROM promocodes WHERE id = ?",
            (promo_id,)
        )
        
        await queries.add_log(
            category="promocode",
            action="deleted_permanent",
            user_id=callback.from_user.id,
            details={"promo_id": promo_id}
        )
        
        await callback.message.edit_text(
            "✅ Промокод удален навсегда.",
            reply_markup=get_admin_back_keyboard("admin_promocodes")
        )
        logger.info(f"Удален промокод id={promo_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении промокода: {e}")
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_"))
async def callback_admin_block_user_confirm(callback: CallbackQuery):
    """Запрос подтверждения блокировки пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[2])
    user = await queries.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    is_blocked = user.get("status") == "blocked"
    action = "разблокировать" if is_blocked else "заблокировать"
    
    await callback.message.edit_text(
        f"⚠️ Ты точно хочешь {action} этого пользователя?",
        reply_markup=get_user_block_confirm_keyboard(user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_block_"))
async def callback_admin_confirm_block_user(callback: CallbackQuery):
    """Подтверждение блокировки пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[3])
    
    try:
        user = await queries.get_user(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        is_blocked = user.get("status") == "blocked"
        new_status = "active" if is_blocked else "blocked"
        
        await queries.set_user_status(user_id, new_status)
        
        action = "разблокирован" if is_blocked else "заблокирован"
        await callback.message.edit_text(
            f"✅ Пользователь {action}.",
            reply_markup=get_admin_back_keyboard(f"admin_user_{user_id}")
        )
        logger.info(f"Пользователь {user_id} {action}")
        
    except Exception as e:
        logger.error(f"Ошибка при блокировке: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()


# ================== РЕДАКТИРОВАНИЕ РЕКВИЗИТОВ ОПЛАТЫ ==================

@router.callback_query(F.data == "admin_payment_details")
async def callback_admin_payment_details(callback: CallbackQuery):
    """Показ реквизитов оплаты."""
    if not is_admin(callback.from_user.id):
        return
    
    payment_details = await queries.get_setting("payment_details") or "Не указаны"
    qiwi_number = await queries.get_setting("qiwi_number") or "Не указан"
    crypto_wallet = await queries.get_setting("crypto_wallet") or "Не указан"
    
    text = (
        f"💳 Реквизиты оплаты:\n\n"
        f"Карта: {payment_details}\n"
        f"QIWI: {qiwi_number}\n"
        f"Крипто: {crypto_wallet}\n\n"
        f"Нажми 'Изменить' для редактирования."
    )
    
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="admin_edit_payment_details")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_other")],
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


# ================== УДАЛЕНИЕ КЛЮЧА ПОЛЬЗОВАТЕЛЯ ==================

@router.callback_query(F.data.startswith("admin_reset_key_"))
async def callback_admin_reset_key(callback: CallbackQuery):
    """Показ ключей пользователя для удаления."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[3])
    keys = await queries.get_user_keys(user_id, active_only=False)
    
    if not keys:
        await callback.message.edit_text(
            "У пользователя нет ключей.",
            reply_markup=get_admin_back_keyboard(f"admin_user_{user_id}")
        )
        await callback.answer()
        return
    
    keyboard = []
    for key in keys:
        status = "✅" if key.get("is_active") else "❌"
        expires = format_date(key.get("expires_at")) if key.get("expires_at") else "N/A"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} Ключ #{key['id']} (до {expires})",
                callback_data=f"admin_delete_user_key_{key['id']}_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data=f"admin_user_{user_id}")])
    
    await callback.message.edit_text(
        "Выбери ключ для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_user_key_"))
async def callback_admin_delete_user_key(callback: CallbackQuery):
    """Подтверждение удаления ключа пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split("_")
    key_id = int(parts[4])
    user_id = int(parts[5])
    
    await callback.message.edit_text(
        "⚠️ Ты точно хочешь удалить этот ключ?",
        reply_markup=get_key_delete_confirm_keyboard(key_id, user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_key_"))
async def callback_admin_confirm_delete_key(callback: CallbackQuery):
    """Подтверждение удаления ключа пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split("_")
    key_id = int(parts[4])
    user_id = int(parts[5])
    
    try:
        key_data = await queries.get_user_key(key_id)
        if not key_data:
            await callback.answer("❌ Ключ не найден", show_alert=True)
            return
        
        # Удаляем с сервера
        server = await queries.get_server(key_data["server_id"])
        if server:
            xui = XuiService(server)
            await xui.delete_client(key_data["key_uuid"])
            await queries.decrement_server_load(key_data["server_id"])
        
        # Удаляем из БД
        await queries.delete_user_key(key_id)
        
        await queries.add_log(
            category="key",
            action="deleted_by_admin",
            user_id=callback.from_user.id,
            target_user_id=user_id,
            details={"key_id": key_id}
        )
        
        await callback.message.edit_text(
            "✅ Ключ удален.",
            reply_markup=get_admin_back_keyboard(f"admin_user_{user_id}")
        )
        logger.info(f"Админ удалил ключ {key_id} пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении ключа: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    

# ================== НОВЫЕ ОБРАБОТЧИКИ ПО ТЗ V2 ==================

# --- РАЗДЕЛ "ПОЛЬЗОВАТЕЛИ" ---

@router.message(F.text == "👥 Пользователи")
async def admin_users_section(message: Message, state: FSMContext):
    """Раздел управления пользователями (1.2)."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "👥 Управление пользователями",
        reply_markup=get_admin_users_menu_keyboard()
    )


@router.callback_query(F.data == "admin_user_search")
async def callback_admin_user_search(callback: CallbackQuery, state: FSMContext):
    """Поиск пользователя (1.2.1)."""
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "🔍 Введи ID или @username пользователя для поиска:",
        reply_markup=get_admin_user_search_keyboard()
    )
    await state.set_state(AdminStates.search_user)
    await callback.answer()


@router.callback_query(F.data == "admin_users_list")
async def callback_admin_users_list(callback: CallbackQuery, state: FSMContext):
    """Список пользователей (1.2.2)."""
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    users = await queries.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "👥 Пользователей пока нет",
            reply_markup=get_admin_users_menu_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"👥 Управление пользователями (всего: {len(users)})",
        reply_markup=get_admin_users_list_keyboard(users, page=0, per_page=8)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users_page_"))
async def callback_admin_users_page(callback: CallbackQuery):
    """Пагинация списка пользователей (1.2.2)."""
    if not is_admin(callback.from_user.id):
        return
    
    page = int(callback.data.split("_")[3])
    users = await queries.get_all_users()
    
    await callback.message.edit_text(
        f"👥 Управление пользователями (всего: {len(users)})",
        reply_markup=get_admin_users_list_keyboard(users, page=page, per_page=8)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_card_"))
async def callback_admin_user_card(callback: CallbackQuery):
    """Карточка пользователя (1.2.3)."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split("_")[3])
    user = await queries.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Формируем карточку по ТЗ
    username = f"@{user['username']}" if user.get('username') else "Нет username"
    balance = format_balance(user.get('balance', 0))
    
    # Статус
    expires_dt = parse_datetime(user.get("expires_at"))
    if user.get("status") == "blocked":
        status = "❌ Заблокирован"
    elif expires_dt and expires_dt > datetime.utcnow():
        status = "✅ Активен"
    else:
        status = "❌ Не активен"
    
    # Трафик
    traffic = user.get("traffic_used", 0)
    traffic_gb = round(traffic / (1024**3), 1) if traffic else 0
    traffic_text = f"{traffic_gb} GB / Безлимит"
    
    # Рефералы
    ref_stats = await queries.get_referral_stats(user_id)
    referrals_count = ref_stats.get("referrals_count", 0)
    referral_earnings = format_balance(ref_stats.get("referral_earnings", 0))
    
    # Ключи
    keys = await queries.get_user_keys(user_id, active_only=True)
    keys_text = f"🔑 Ключей: {len(keys)}\n"
    if keys:
        for i, key in enumerate(keys, 1):
            days_left = get_days_left(key.get("expires_at"))
            flag = get_country_flag(key.get("country_code", ""))
            keys_text += f"• Ключ #{i} — до {format_date(key.get('expires_at'))} (осталось {days_left} дн) — {flag}\n"
    
    text = (
        f"👤 {username}\n"
        f"🆔 ID: {user_id}\n\n"
        f"📅 Регистрация: {format_date(user.get('registered_at'))}\n"
        f"💎 Статус: {status}\n"
        f"💰 Баланс: {balance} ₽\n"
        f"📊 Трафик: {traffic_text}\n\n"
        f"🎁 Рефералов: {referrals_count}\n"
        f"🎁 Заработано: {referral_earnings} ₽\n\n"
        f"{keys_text}"
    )
    
    is_blocked = user.get("status") == "blocked"
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_user_card_keyboard(user_id, is_blocked=is_blocked)
    )
    await callback.answer()


# --- РАЗДЕЛ "СТАТИСТИКА" ---

@router.message(F.text == "📊 Статистика")
async def admin_stats_section(message: Message):
    """Раздел статистики (1.3)."""
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
    servers_stats = await queries.get_servers_with_load()
    
    servers_text = ""
    for stat in servers_stats:
        flag = get_country_flag(stat["country_code"])
        status = "✅" if stat["is_active"] else "❌"
        load_percent = int(stat.get("load", 0) / max(stat.get("capacity", 200), 1) * 100)
        servers_text += f"{status} {flag} {stat['name']} — {stat.get('users_count', 0)} польз. — нагрузка {load_percent}%\n"
    
    text = (
        f"📊 Статистика {BOT_NAME}\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Активных сегодня: {active_today}\n"
        f"🆕 Новых за сегодня: {new_today}\n\n"
        f"💰 Общий баланс: {format_balance(total_balance)} ₽\n"
        f"💵 Продажи за месяц: {format_balance(month_sales)} ₽\n"
        f"📊 Средний чек: {format_balance(avg_check)} ₽\n\n"
        f"🌍 По серверам:\n{servers_text or 'Нет серверов'}"
    )
    
    await message.answer(text, reply_markup=get_admin_stats_keyboard())


@router.callback_query(F.data == "admin_stats_refresh")
async def callback_admin_stats_refresh(callback: CallbackQuery):
    """Обновление статистики."""
    if not is_admin(callback.from_user.id):
        return
    
    await admin_stats_section(callback.message)
    await callback.answer()


# --- РАЗДЕЛ "СЕРВЕРЫ" ---

@router.message(F.text == "🌍 Серверы")
async def admin_servers_section(message: Message, state: FSMContext):
    """Раздел управления серверами (1.4)."""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    servers = await queries.get_servers_with_load()
    
    text = "🌍 Управление серверами\n\n"
    
    if servers:
        for s in servers:
            status = "✅" if s.get("is_active") else "❌"
            flag = get_country_flag(s.get("country_code", ""))
            users = s.get("users_count", 0)
            capacity = s.get("capacity", 200) or 200
            load = int(users / capacity * 100) if capacity > 0 else 0
            text += f"{status} {flag} {s['name']} — {users} польз. — нагрузка {load}%\n"
    
    await message.answer(text, reply_markup=get_admin_servers_list_keyboard(servers))


@router.callback_query(F.data.startswith("admin_server_card_"))
async def callback_admin_server_card(callback: CallbackQuery):
    """Карточка сервера (1.4.2)."""
    if not is_admin(callback.from_user.id):
        return
    
    server_id = int(callback.data.split("_")[3])
    server = await queries.get_server(server_id)
    
    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return
    
    flag = get_country_flag(server.get("country_code", ""))
    status = "✅ Активен" if server.get("is_active") else "❌ Неактивен"
    load = server.get("load", 0)
    capacity = server.get("capacity", 200) or 200
    load_percent = int(load / capacity * 100) if capacity > 0 else 0
    ping = server.get("ping", 0)
    
    # Количество пользователей
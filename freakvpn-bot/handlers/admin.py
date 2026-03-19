"""
Хендлер админ-панели.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from loguru import logger

from config import ADMIN_IDS, BOT_NAME
from database.models import User
from database.queries import (
    get_user_by_id, get_user_by_username, update_user, create_transaction,
    get_all_users, get_stats, get_active_servers, create_server,
    get_tariffs, update_setting, get_setting
)
from keyboards.reply import get_admin_keyboard, get_main_keyboard
from keyboards.inline import (
    get_admin_user_keyboard, get_admin_confirm_keyboard,
    get_admin_servers_keyboard, get_admin_server_keyboard,
    get_admin_mailing_keyboard, get_admin_settings_keyboard,
    get_admin_back_keyboard
)
from utils.constants import ADMIN_WELCOME, ADMIN_USER_INFO, ADMIN_STATS, ADMIN_SERVERS_LIST
from utils.helpers import format_balance, format_datetime
from utils.validators import extract_user_id_or_username, is_valid_amount

router = Router()


# FSM состояния
class AdminStates(StatesGroup):
    search_user = State()
    add_balance_amount = State()
    add_server = State()
    mailing = State()
    edit_setting = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id in ADMIN_IDS


@router.message(F.text == "/admin")
async def cmd_admin(message: Message, user: User):
    """Вход в админ-панель."""
    if not is_admin(user.user_id):
        # Игнорируем сообщение для не-админов
        return
    
    text = ADMIN_WELCOME.format(bot_name=BOT_NAME)
    
    await message.answer(
        text,
        reply_markup=get_admin_keyboard()
    )
    logger.info(f"Админ {user.user_id} вошёл в админ-панель")


# === ПОЛЬЗОВАТЕЛИ ===

@router.message(F.text == "👥 Пользователи")
async def admin_users(message: Message, state: FSMContext):
    """Поиск пользователя."""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("🔍 Введи ID или @username пользователя для поиска:")
    await state.set_state(AdminStates.search_user)


@router.message(AdminStates.search_user)
async def admin_search_user(message: Message, state: FSMContext):
    """Обработка поиска пользователя."""
    if not is_admin(message.from_user.id):
        return
    
    user_id, username = extract_user_id_or_username(message.text)
    
    target_user = None
    
    if user_id:
        target_user = await get_user_by_id(user_id)
    elif username:
        target_user = await get_user_by_username(username)
    
    if not target_user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    # Формируем информацию о пользователе
    status = "Активен" if target_user.is_active else "Не активен"
    key_preview = target_user.current_key[:30] + "..." if target_user.current_key else "Нет"
    
    text = ADMIN_USER_INFO.format(
        username=target_user.username or "Нет username",
        user_id=target_user.user_id,
        registered_at=format_datetime(target_user.registered_at),
        status=status,
        server="Не выбран",
        balance=format_balance(target_user.balance),
        key=key_preview
    )
    
    await message.answer(
        text,
        reply_markup=get_admin_user_keyboard(target_user.user_id)
    )
    await state.clear()


# === ПОПОЛНЕНИЕ БАЛАНСА ===

@router.message(F.text == "💰 Пополнить баланс")
async def admin_balance(message: Message, state: FSMContext):
    """Пополнение баланса пользователя."""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("💰 Введи ID пользователя:")
    await state.set_state(AdminStates.add_balance_amount)
    await state.update_data(admin_action="balance", step="user_id")


@router.callback_query(F.data.startswith("admin_add_balance_"))
async def cb_admin_add_balance(callback: CallbackQuery, state: FSMContext):
    """Начисление баланса через callback."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("admin_add_balance_", ""))
    
    await state.update_data(admin_action="balance", target_user_id=user_id)
    await state.set_state(AdminStates.add_balance_amount)
    
    target_user = await get_user_by_id(user_id)
    
    await callback.message.edit_text(
        f"💰 Пополнение баланса\n\n"
        f"ID: {user_id}\n"
        f"Username: @{target_user.username if target_user else 'неизвестно'}\n"
        f"Текущий баланс: {format_balance(target_user.balance) if target_user else 0} ₽\n\n"
        f"Введи сумму для начисления (в рублях):"
    )
    await callback.answer()


@router.message(AdminStates.add_balance_amount)
async def admin_balance_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения."""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    
    if data.get("step") == "user_id":
        # Получили ID пользователя, запрашиваем сумму
        user_id, username = extract_user_id_or_username(message.text)
        
        if not user_id:
            await message.answer("❌ Неверный формат ID")
            return
        
        target_user = await get_user_by_id(user_id)
        
        if not target_user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        await state.update_data(target_user_id=user_id)
        await state.update_data(step="amount")
        
        await message.answer(
            f"💰 Пополнение баланса\n\n"
            f"ID: {user_id}\n"
            f"Username: @{target_user.username or 'нет'}\n"
            f"Текущий баланс: {format_balance(target_user.balance)} ₽\n\n"
            f"Введи сумму для начисления (в рублях):"
        )
        return
    
    # Получили сумму
    if not is_valid_amount(message.text):
        await message.answer("❌ Неверная сумма. Введи число от 1 до 1000000")
        return
    
    amount_rub = float(message.text)
    amount_kopecks = int(amount_rub * 100)
    
    target_user_id = data.get("target_user_id")
    target_user = await get_user_by_id(target_user_id)
    
    if not target_user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    new_balance = target_user.balance + amount_kopecks
    
    await message.answer(
        f"💰 Подтверждение начисления\n\n"
        f"Пользователь: @{target_user.username or target_user.user_id}\n"
        f"Сумма: +{amount_rub:.0f} ₽\n"
        f"Текущий баланс: {format_balance(target_user.balance)} ₽\n"
        f"Новый баланс: {format_balance(new_balance)} ₽",
        reply_markup=get_admin_confirm_keyboard("add_balance", target_user_id, amount_kopecks)
    )
    
    await state.clear()


@router.callback_query(F.data.startswith("admin_confirm_add_balance_"))
async def cb_confirm_add_balance(callback: CallbackQuery):
    """Подтверждение начисления баланса."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split("_")
    amount_kopecks = int(parts[-2])
    user_id = int(parts[-1])
    
    target_user = await get_user_by_id(user_id)
    
    if not target_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Начисляем баланс
    new_balance = target_user.balance + amount_kopecks
    await update_user(user_id, balance=new_balance)
    
    # Создаём транзакцию
    await create_transaction(
        user_id=user_id,
        amount=amount_kopecks,
        transaction_type="admin",
        description="Пополнение от администратора",
        admin_id=callback.from_user.id
    )
    
    # Уведомляем админа
    await callback.message.edit_text(
        f"✅ Баланс пополнен!\n\n"
        f"Пользователь: @{target_user.username or user_id}\n"
        f"Начислено: +{format_balance(amount_kopecks)} ₽\n"
        f"Новый баланс: {format_balance(new_balance)} ₽"
    )
    
    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            user_id,
            f"💰 Баланс пополнен!\n\n"
            f"Тебе начислено: +{format_balance(amount_kopecks)} ₽\n"
            f"Текущий баланс: {format_balance(new_balance)} ₽\n\n"
            f"Спасибо за доверие к {BOT_NAME}! ❤️"
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    await callback.answer()
    logger.info(f"Админ {callback.from_user.id} начислил {format_balance(amount_kopecks)} ₽ пользователю {user_id}")


# === СТАТИСТИКА ===

@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    """Показывает статистику."""
    if not is_admin(message.from_user.id):
        return
    
    stats = await get_stats()
    
    text = ADMIN_STATS.format(
        bot_name=BOT_NAME,
        total_users=stats["total_users"],
        active_today=stats["active_today"],
        new_today=stats["new_today"],
        total_balance=format_balance(stats["total_balance"]),
        month_sales=format_balance(stats["month_sales"]),
        avg_check=format_balance(stats["month_sales"] // max(stats["total_users"], 1)),
        servers_stats="Данные отсутствуют"
    )
    
    await message.answer(text)


# === СЕРВЕРЫ ===

@router.message(F.text == "🌍 Серверы")
async def admin_servers(message: Message):
    """Управление серверами."""
    if not is_admin(message.from_user.id):
        return
    
    servers = await get_active_servers()
    
    servers_list = []
    servers_users = []
    
    for server in servers:
        status = "✅" if server.is_active else "❌"
        servers_list.append(f"{status} {server.flag} {server.name} ({server.domain}) — X-UI: {server.api_url}")
        servers_users.append(f"{server.flag} {server.name}: {server.user_count} пользователей")
    
    text = ADMIN_SERVERS_LIST.format(
        servers_list="\n".join(servers_list) if servers_list else "Нет серверов",
        servers_users="\n".join(servers_users) if servers_users else "Нет данных"
    )
    
    await message.answer(
        text,
        reply_markup=get_admin_servers_keyboard(servers)
    )


@router.callback_query(F.data == "admin_add_server")
async def cb_admin_add_server(callback: CallbackQuery, state: FSMContext):
    """Добавление сервера."""
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "➕ Добавление нового сервера\n\n"
        "Введи данные в формате:\n"
        "Название;Код_страны;Домен;IP;API_URL;API_логин;API_пароль;Порт\n\n"
        "Пример:\n"
        "Амстердам;NL;ams.freakvpn.ru;45.67.89.10;http://45.67.89.10:54321;admin;pass123;443"
    )
    await state.set_state(AdminStates.add_server)
    await callback.answer()


@router.message(AdminStates.add_server)
async def admin_add_server_process(message: Message, state: FSMContext):
    """Обработка добавления сервера."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split(";")
        
        if len(parts) < 7:
            await message.answer("❌ Неверный формат. Нужно минимум 7 параметров через точку с запятой")
            return
        
        name = parts[0].strip()
        country_code = parts[1].strip().upper()
        domain = parts[2].strip()
        ip = parts[3].strip()
        api_url = parts[4].strip()
        api_username = parts[5].strip()
        api_password = parts[6].strip()
        port = int(parts[7].strip()) if len(parts) > 7 else 443
        
        server = await create_server(
            name=name,
            country_code=country_code,
            domain=domain,
            ip=ip,
            api_url=api_url,
            api_username=api_username,
            api_password=api_password,
            port=port
        )
        
        await message.answer(f"✅ Сервер {name} успешно добавлен!")
        logger.info(f"Админ {message.from_user.id} добавил сервер {name}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()


# === РАССЫЛКА ===

@router.message(F.text == "✉️ Рассылка")
async def admin_mailing(message: Message, state: FSMContext):
    """Создание рассылки."""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "📨 Создание рассылки\n\n"
        "Отправь мне сообщение (текст, фото или видео), которое хочешь разослать всем пользователям."
    )
    await state.set_state(AdminStates.mailing)


@router.message(AdminStates.mailing)
async def admin_mailing_content(message: Message, state: FSMContext):
    """Получение контента для рассылки."""
    if not is_admin(message.from_user.id):
        return
    
    # Получаем всех пользователей
    users = await get_all_users()
    
    # Сохраняем контент
    await state.update_data(
        mailing_content=message.html_text,
        mailing_content_type="text"
    )
    
    await message.answer(
        f"📨 Предпросмотр рассылки:\n\n"
        f"{message.html_text}\n\n"
        f"Будет отправлено: {len(users)} пользователям",
        reply_markup=get_admin_mailing_keyboard(len(users))
    )


@router.callback_query(F.data == "admin_send_test")
async def cb_admin_send_test(callback: CallbackQuery, state: FSMContext):
    """Тестовая рассылка админу."""
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    content = data.get("mailing_content", "")
    
    await callback.bot.send_message(
        callback.from_user.id,
        content,
        parse_mode="HTML"
    )
    
    await callback.answer("✅ Тестовое сообщение отправлено!")
    await state.clear()


@router.callback_query(F.data == "admin_send_all")
async def cb_admin_send_all(callback: CallbackQuery, state: FSMContext):
    """Рассылка всем пользователям."""
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    content = data.get("mailing_content", "")
    
    users = await get_all_users()
    sent = 0
    failed = 0
    
    await callback.message.edit_text(f"📨 Рассылка начата...\n\nОтправлено: 0 / {len(users)}")
    
    for user in users:
        try:
            await callback.bot.send_message(
                user.user_id,
                content,
                parse_mode="HTML"
            )
            sent += 1
            
            # Обновляем статус каждые 10 сообщений
            if sent % 10 == 0:
                await callback.message.edit_text(f"📨 Рассылка...\n\nОтправлено: {sent} / {len(users)}")
        
        except Exception:
            failed += 1
    
    await callback.message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"Отправлено: {sent}\n"
        f"Не удалось: {failed}"
    )
    
    logger.info(f"Админ {callback.from_user.id} сделал рассылку. Отправлено: {sent}, Ошибок: {failed}")
    await state.clear()


# === НАСТРОЙКИ ===

@router.message(F.text == "⚙️ Настройки")
async def admin_settings(message: Message):
    """Настройки бота."""
    if not is_admin(message.from_user.id):
        return
    
    tariffs = await get_tariffs()
    trial_days = await get_setting("trial_days") or "3"
    referral_bonus = await get_setting("referral_bonus") or "5000"
    
    tariffs_text = "\n".join([
        f"{t.name}: {format_balance(t.price)} ₽"
        for t in tariffs
    ])
    
    text = f"""⚙️ Настройки бота

💰 Тарифы:
{tariffs_text}

🎁 Пробный период: {trial_days} дней
👥 Реферальный бонус: {format_balance(int(referral_bonus))} ₽"""
    
    await message.answer(
        text,
        reply_markup=get_admin_settings_keyboard()
    )


@router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена действия."""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено")
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery):
    """Возврат назад."""
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_"))
async def cb_admin_block(callback: CallbackQuery):
    """Блокировка пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("admin_block_", ""))
    
    await update_user(user_id, status="blocked")
    
    await callback.answer("✅ Пользователь заблокирован")
    logger.info(f"Админ {callback.from_user.id} заблокировал пользователя {user_id}")


@router.callback_query(F.data.startswith("admin_unblock_"))
async def cb_admin_unblock(callback: CallbackQuery):
    """Разблокировка пользователя."""
    if not is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("admin_unblock_", ""))
    
    await update_user(user_id, status="active")
    
    await callback.answer("✅ Пользователь разблокирован")
    logger.info(f"Админ {callback.from_user.id} разблокировал пользователя {user_id}")

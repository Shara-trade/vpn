"""
Обработчики раздела 'Мои ключи'.
Поддержка до 5 активных ключей с переключением.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime

from database import queries
from keyboards import (
    get_keys_keyboard, get_key_change_confirm_keyboard, get_key_delete_confirm_keyboard,
    get_keys_empty_keyboard, get_back_and_close_keyboard, get_main_keyboard,
    get_subscription_check_keyboard
)
from utils.constants import KEYS_MESSAGE, KEYS_EMPTY_MESSAGE, KEY_CHANGE_CONFIRM_MESSAGE, KEY_DELETE_CONFIRM_MESSAGE
from utils.helpers import format_date, get_days_left
from services.xui_api import XuiService
from handlers.start import check_channel_subscription

router = Router()


async def show_keys(message: Message, db_user: dict = None, key_index: int = 0):
    """Показ списка ключей пользователя с переключением."""
    user_id = db_user["user_id"] if db_user else message.from_user.id
    
    keys = await queries.get_user_keys(user_id, active_only=True)
    
    if not keys:
        await message.answer(KEYS_EMPTY_MESSAGE, reply_markup=get_keys_empty_keyboard())
        return
    
    if key_index < 0:
        key_index = 0
    if key_index >= len(keys):
        key_index = len(keys) - 1
    
    current_key = keys[key_index]
    days_left = get_days_left(current_key["expires_at"])
    auto_renew_status = "✅ Вкл" if current_key["auto_renew"] else "❌ Выкл"
    
    await message.answer(
        KEYS_MESSAGE.format(
            key_index=key_index + 1,
            expires_at=format_date(current_key["expires_at"]),
            days_left=days_left,
            server_name=current_key.get("server_name", "Неизвестно"),
            auto_renew_status=auto_renew_status,
            key=current_key["key"]
        ),
        reply_markup=get_keys_keyboard(
            key_id=current_key["id"],
            has_prev=(key_index > 0),
            has_next=(key_index < len(keys) - 1),
            auto_renew=current_key["auto_renew"],
            server_id=current_key["server_id"]
        )
    )


@router.callback_query(F.data.startswith("key_prev_"))
async def callback_key_prev(callback: CallbackQuery, db_user: dict = None):
    """Переход к предыдущему ключу."""
    current_key_id = int(callback.data.split("_")[2])
    keys = await queries.get_user_keys(callback.from_user.id, active_only=True)
    current_index = next((i for i, k in enumerate(keys) if k["id"] == current_key_id), 0)
    await callback.message.delete()
    await show_keys(callback.message, db_user, current_index - 1)
    await callback.answer()


@router.callback_query(F.data.startswith("key_next_"))
async def callback_key_next(callback: CallbackQuery, db_user: dict = None):
    """Переход к следующему ключу."""
    current_key_id = int(callback.data.split("_")[2])
    keys = await queries.get_user_keys(callback.from_user.id, active_only=True)
    current_index = next((i for i, k in enumerate(keys) if k["id"] == current_key_id), 0)
    await callback.message.delete()
    await show_keys(callback.message, db_user, current_index + 1)
    await callback.answer()


@router.callback_query(F.data.startswith("key_details_"))
async def callback_key_details(callback: CallbackQuery, db_user: dict = None):
    """Обновление деталей ключа."""
    key_id = int(callback.data.split("_")[2])
    keys = await queries.get_user_keys(callback.from_user.id, active_only=True)
    current_index = next((i for i, k in enumerate(keys) if k["id"] == key_id), 0)
    await callback.message.delete()
    await show_keys(callback.message, db_user, current_index)
    await callback.answer()


@router.callback_query(F.data.startswith("copy_key_"))
async def callback_copy_key(callback: CallbackQuery):
    """Копирование ключа."""
    await callback.answer("Ключ скопирован в буфер обмена!", show_alert=False)


@router.callback_query(F.data.startswith("extend_key_"))
async def callback_extend_key(callback: CallbackQuery, db_user: dict = None):
    """Продление ключа - переход к тарифам."""
    key_id = int(callback.data.split("_")[2])
    await callback.message.delete()
    from handlers.purchase import show_buy_menu
    await show_buy_menu(callback.message, db_user, extend_key_id=key_id)
    await callback.answer()


@router.callback_query(F.data.startswith("change_key_"))
async def callback_change_key(callback: CallbackQuery):
    """Запрос подтверждения смены ключа."""
    key_id = int(callback.data.split("_")[2])
    is_subscribed = await check_channel_subscription(callback.bot, callback.from_user.id)
    if not is_subscribed:
        await callback.message.edit_text("<b>Для смены ключа необходимо подписаться на новостной канал.</b>", reply_markup=get_subscription_check_keyboard(f"change_key_{key_id}"))
        await callback.answer()
        return
    await callback.message.edit_text(KEY_CHANGE_CONFIRM_MESSAGE, reply_markup=get_key_change_confirm_keyboard(key_id))
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_change_key_"))
async def callback_confirm_change_key(callback: CallbackQuery, db_user: dict = None):
    """Подтверждение смены ключа."""
    key_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    key_data = await queries.get_user_key(key_id)
    if not key_data:
        await callback.answer("❌ Ключ не найден", show_alert=True)
        return
    new_server = await queries.select_best_server()
    if not new_server:
        await callback.answer("❌ Нет доступных серверов", show_alert=True)
        return
    try:
        old_server = await queries.get_server(key_data["server_id"])
        if old_server:
            old_xui = XuiService(old_server)
            await old_xui.delete_client(key_data["key_uuid"])
            await queries.decrement_server_load(old_server["id"])
    except Exception as e:
        logger.warning(f"Не удалось удалить старый ключ: {e}")
    xui = XuiService(new_server)
    try:
        expires_dt = key_data.get("expires_at")
        if isinstance(expires_dt, str):
            expires_dt = datetime.fromisoformat(expires_dt.replace("Z", "+00:00"))
        days_left = max(1, (expires_dt - datetime.utcnow()).days) if expires_dt else 30
        new_key = await xui.create_client(user_id, days=days_left)
        if not new_key:
            await callback.answer("❌ Ошибка при создании нового ключа", show_alert=True)
            return
        await queries.increment_server_load(new_server["id"])
        await queries.delete_user_key(key_id)
        await queries.create_user_key(user_id=user_id, key=new_key["key"], key_uuid=new_key["uuid"], server_id=new_server["id"], expires_at=key_data["expires_at"], auto_renew=key_data["auto_renew"])
        await callback.message.edit_text(f"✅ Ключ успешно изменен!\n\n🌍 Новый сервер: {new_server['name']}\n🔑 Новый ключ:\n<code>{new_key['key']}</code>", reply_markup=get_back_and_close_keyboard("go_to_keys"))
        logger.info(f"Ключ изменен: user_id={user_id}, old_key_id={key_id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при смене ключа: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_key_"))
async def callback_delete_key(callback: CallbackQuery):
    """Запрос подтверждения удаления ключа."""
    key_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(KEY_DELETE_CONFIRM_MESSAGE, reply_markup=get_key_delete_confirm_keyboard(key_id))
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_key_"))
async def callback_confirm_delete_key(callback: CallbackQuery, db_user: dict = None):
    """Подтверждение удаления ключа."""
    key_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    key_data = await queries.get_user_key(key_id)
    if not key_data:
        await callback.answer("❌ Ключ не найден", show_alert=True)
        return
    try:
        server = await queries.get_server(key_data["server_id"])
        if server:
            xui = XuiService(server)
            await xui.delete_client(key_data["key_uuid"])
            await queries.decrement_server_load(server["id"])
    except Exception as e:
        logger.warning(f"Не удалось удалить ключ с сервера: {e}")
    await queries.delete_user_key(key_id)
    await queries.add_log(category="key", action="key_deleted", user_id=user_id, details={"key_id": key_id})
    await callback.message.edit_text("✅ Ключ удален.", reply_markup=get_back_and_close_keyboard("go_to_keys"))
    logger.info(f"Ключ удален: user_id={user_id}, key_id={key_id}")
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_autorenew_"))
async def callback_toggle_autorenew(callback: CallbackQuery):
    """Включение/выключение автопродления."""
    key_id = int(callback.data.split("_")[2])
    key_data = await queries.get_user_key(key_id)
    if not key_data:
        await callback.answer("❌ Ключ не найден", show_alert=True)
        return
    new_state = not key_data["auto_renew"]
    await queries.set_key_auto_renew(key_id, new_state)
    status_text = "включено" if new_state else "отключено"
    await callback.answer(f"Автопродление {status_text}", show_alert=False)
    await callback.message.delete()
    await show_keys(callback.message, await queries.get_user(callback.from_user.id))


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
    await callback.answer()
    await callback.message.answer(guide_text)


@router.callback_query(F.data == "go_to_keys")
async def callback_go_to_keys(callback: CallbackQuery, db_user: dict = None):
    """Переход в раздел 'Мои ключи'."""
    await callback.message.delete()
    await show_keys(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "go_to_buy")
async def callback_go_to_buy(callback: CallbackQuery, db_user: dict = None):
    """Переход в раздел 'Купить'."""
    from handlers.purchase import show_buy_menu
    await callback.message.delete()
    await show_buy_menu(callback.message, db_user)
    await callback.answer()
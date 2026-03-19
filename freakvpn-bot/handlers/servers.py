"""
Хендлер серверов.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import User
from database.queries import get_active_servers, get_server_by_id, update_user
from keyboards.inline import get_servers_keyboard
from utils.constants import SERVERS_LIST, SERVER_CHANGED

router = Router()


@router.callback_query(F.data == "change_server")
async def cb_change_server(callback: CallbackQuery, user: User):
    """Выбор сервера."""
    servers = await get_active_servers()
    
    if not servers:
        await callback.answer("❌ Нет доступных серверов", show_alert=True)
        return
    
    # Формируем список серверов
    servers_text = []
    for server in servers:
        ping_text = f"{server.ping} ms" if server.ping else "N/A"
        servers_text.append(f"{server.flag} {server.name} — {ping_text}")
    
    text = SERVERS_LIST.format(
        servers_list="\n".join(servers_text)
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_servers_keyboard(servers, user.server_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_server_"))
async def cb_select_server(callback: CallbackQuery, user: User):
    """Выбор конкретного сервера."""
    server_id = int(callback.data.split("_")[-1])
    
    server = await get_server_by_id(server_id)
    
    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return
    
    # Проверяем, не тот же самый сервер
    if user.server_id == server_id:
        await callback.answer("✅ Вы уже используете этот сервер")
        return
    
    # Обновляем сервер пользователя
    await update_user(user.user_id, server_id=server_id)
    
    # Здесь должна быть генерация нового ключа через X-UI API
    # Пока используем заглушку
    new_key = f"vless://test-uuid@{server.domain}:{server.port}?security=tls&type=tcp#FreakVPN_{server.country_code}"
    
    text = SERVER_CHANGED.format(
        server_name=server.display_name,
        server_domain=server.domain,
        key=new_key
    )
    
    await callback.message.edit_text(text)
    await callback.answer("✅ Сервер изменён!")


@router.callback_query(F.data == "servers_info")
async def cb_servers_info(callback: CallbackQuery, user: User):
    """Информация о серверах."""
    servers = await get_active_servers()
    
    text = """🌍 Как выбрать сервер?

Выбирай сервер с минимальным пингом для лучшей скорости.

📌 Рекомендации:
• 🇳🇱 Амстердам — оптимален для СНГ
• 🇩🇪 Франкфурт — хорош для Европы
• 🇫🇮 Хельсинки — ближайший к РФ
• 🇺🇸 Нью-Йорк — для доступа к US контенту
• 🇸🇬 Сингапур — для Азии

💡 Ты можешь сменить сервер в любой момент без потери подписки."""
    
    await callback.message.edit_text(text)
    await callback.answer()

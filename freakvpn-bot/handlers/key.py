"""
Хендлер ключа.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import BOT_NAME
from database.models import User
from database.queries import get_server_by_id
from keyboards.inline import get_key_keyboard
from utils.constants import KEY_INFO, ERROR_NO_KEY

router = Router()


async def show_key(message: Message, user: User):
    """Показывает ключ пользователя."""
    if not user.current_key:
        await message.answer(
            ERROR_NO_KEY,
            reply_markup=None
        )
        return
    
    # Получаем сервер
    server_name = "Неизвестно"
    server_domain = "unknown"
    
    if user.server_id:
        server = await get_server_by_id(user.server_id)
        if server:
            server_name = server.display_name
            server_domain = server.domain
    
    text = KEY_INFO.format(
        bot_name=BOT_NAME,
        server_name=server_name,
        server_domain=server_domain,
        key=user.current_key
    )
    
    await message.answer(
        text,
        reply_markup=get_key_keyboard()
    )


@router.callback_query(F.data == "go_to_key")
async def cb_go_to_key(callback: CallbackQuery, user: User):
    """Переход в раздел ключа."""
    await show_key(callback.message, user)
    await callback.answer()


@router.callback_query(F.data == "copy_key")
async def cb_copy_key(callback: CallbackQuery, user: User):
    """Копирование ключа (просто уведомление)."""
    await callback.answer("Ключ скопирован в буфер обмена!", show_alert=True)


@router.callback_query(F.data == "guide_ios")
async def cb_guide_ios(callback: CallbackQuery, user: User):
    """Инструкция для iOS."""
    text = """📱 Инструкция для iOS:

1. Скачай v2RayTun из App Store
2. Открой приложение
3. Нажми "+" в правом верхнем углу
4. Выбери "Импорт по ссылке"
5. Вставь скопированный ключ
6. Разреши установку VPN-профиля
7. Нажми переключатель для подключения

💡 Рекомендуем включить функцию "Режим VPN" для полной защиты трафика."""
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "guide_android")
async def cb_guide_android(callback: CallbackQuery, user: User):
    """Инструкция для Android."""
    text = """🤖 Инструкция для Android:

1. Скачай v2RayTun из Google Play
2. Открой приложение
3. Нажми "+" в правом нижнем углу
4. Выбери "Импорт из буфера"
5. Вставь скопированный ключ
6. Нажми переключатель для подключения

💡 Рекомендуем включить функцию "Режим VPN" для полной защиты трафика."""
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "guide_main")
async def cb_guide_main(callback: CallbackQuery, user: User):
    """Основная инструкция."""
    text = """📱 Инструкция по подключению:

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
    
    await callback.message.edit_text(text)
    await callback.answer()

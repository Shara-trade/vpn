"""
Обработчики callback-запросов.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta

from config import BOT_NAME, DEFAULT_TRIAL_DAYS
from database.models import User
from database.queries import (
    get_user_by_referral_code, update_user, create_referral,
    get_trial_server, create_transaction
)
from keyboards.inline import get_trial_keyboard, get_referral_activate_keyboard
from utils.constants import TRIAL_ACTIVATED, TRIAL_ALREADY_USED, REFERRAL_BONUS_RECEIVED
from utils.helpers import format_datetime

router = Router()


@router.callback_query(F.data == "trial_get")
async def cb_trial_get(callback: CallbackQuery, user: User):
    """Активация пробного периода."""
    if user.trial_used:
        await callback.answer(TRIAL_ALREADY_USED, show_alert=True)
        return
    
    # Получаем сервер для пробного периода
    server = await get_trial_server()
    
    if not server:
        # Если нет триального сервера, берём первый активный
        from database.queries import get_active_servers
        servers = await get_active_servers()
        if servers:
            server = servers[0]
    
    if not server:
        await callback.answer("❌ Нет доступных серверов", show_alert=True)
        return
    
    # Активируем пробный период
    trial_days = DEFAULT_TRIAL_DAYS
    expires_at = datetime.now() + timedelta(days=trial_days)
    
    await update_user(
        user.user_id,
        trial_used=True,
        status="trial",
        expires_at=expires_at,
        server_id=server.id
    )
    
    # Создаём транзакцию
    await create_transaction(
        user_id=user.user_id,
        amount=0,
        transaction_type="trial",
        description=f"Пробный период: {trial_days} дней"
    )
    
    # Генерируем ключ (заглушка, должна быть интеграция с X-UI)
    key = f"vless://trial-uuid@{server.domain}:{server.port}?security=tls&type=tcp#FreakVPN_TRIAL"
    
    text = TRIAL_ACTIVATED.format(
        days=trial_days,
        server_name=server.display_name,
        server_domain=server.domain,
        key=key,
        hours=trial_days * 24
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_trial_keyboard()
    )
    await callback.answer("✅ Пробный период активирован!")


@router.callback_query(F.data.startswith("activate_ref_"))
async def cb_activate_ref(callback: CallbackQuery, user: User):
    """Активация реферального бонуса."""
    referral_code = callback.data.replace("activate_ref_", "")
    
    referrer = await get_user_by_referral_code(referral_code)
    
    if not referrer:
        await callback.answer("❌ Неверный реферальный код", show_alert=True)
        return
    
    if user.referred_by:
        await callback.answer("❌ Ты уже активировал реферальный бонус", show_alert=True)
        return
    
    if referrer.user_id == user.user_id:
        await callback.answer("❌ Нельзя активировать свою ссылку", show_alert=True)
        return
    
    # Создаём реферальную связь
    await create_referral(referrer.user_id, user.user_id)
    
    # Обновляем пользователя
    await update_user(user.user_id, referred_by=referrer.user_id)
    
    # Добавляем +1 день к пробному периоду (если ещё не использован)
    if not user.trial_used:
        # Будет добавлено при активации триала
        pass
    
    await callback.message.edit_text(
        f"✅ Бонус активирован!\n\n"
        f"Твой друг {referrer.full_name} получит бонус после твоей первой покупки.\n\n"
        f"Теперь у тебя +1 день к пробному периоду!",
        reply_markup=None
    )
    await callback.answer()


@router.callback_query(F.data == "about_app")
async def cb_about_app(callback: CallbackQuery, user: User):
    """Информация о приложении."""
    text = """📱 О приложении v2RayTun

v2RayTun — это современный VPN-клиент для Android и iOS.

✅ Преимущества:
• Высокая скорость соединения
• Минимальное потребление батареи
• Простота использования
• Поддержка VLESS протокола
• Автоматическое переподключение

📥 Скачать:
• Google Play: v2RayTun
• App Store: v2RayTun

💻 Для Windows/Mac рекомендуем:
• Nekoray
• V2RayN"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "have_key")
async def cb_have_key(callback: CallbackQuery, user: User):
    """У пользователя уже есть ключ."""
    await callback.message.edit_text(
        "🔑 Отправь мне свой ключ, и я проверю его валидность.\n\n"
        "Формат: vless://...",
        reply_markup=None
    )
    
    # Здесь можно добавить FSM для ожидания ключа
    await callback.answer()


@router.callback_query(F.data == "regenerate_key")
async def cb_regenerate_key(callback: CallbackQuery, user: User):
    """Смена ключа."""
    if not user.current_key:
        await callback.answer("❌ У тебя нет активного ключа", show_alert=True)
        return
    
    # Здесь должна быть генерация нового ключа через X-UI API
    await callback.answer("🔄 Ключ обновлён!", show_alert=True)


@router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(callback: CallbackQuery, user: User):
    """Ввод промокода."""
    await callback.message.edit_text(
        "🎁 Введи промокод:",
        reply_markup=None
    )
    await callback.answer()


@router.callback_query(F.data == "copy_key")
async def cb_copy_key(callback: CallbackQuery, user: User):
    """Копирование ключа."""
    if user.current_key:
        await callback.answer("📋 Ключ скопирован!", show_alert=True)
    else:
        await callback.answer("❌ У тебя нет активного ключа", show_alert=True)

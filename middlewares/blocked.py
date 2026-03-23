"""
Middleware для блокировки пользователей.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger

from config import config


class CancelHandler(Exception):
	"""Исключение для отмены обработки хендлера."""
	pass


class BlockedUserMiddleware(BaseMiddleware):
	"""
	Middleware для блокировки пользователей.
	Проверяет статус пользователя перед обработкой запроса.
	"""

	async def __call__(
		self,
		handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
		event: TelegramObject,
		data: Dict[str, Any]
	) -> Any:
		"""
		Выполнение middleware.
		"""
		# Получаем пользователя из события
		user = data.get("event_from_user")

		# Если пользователя нет в событии — пропускаем
		if not user:
			return await handler(event, data)

		# Админы не блокируются
		if user.id in config.ADMIN_IDS:
			return await handler(event, data)

		# Проверяем статус пользователя в БД
		db_user = data.get("db_user")

		# Если пользователя нет в БД — пропускаем (новый пользователь)
		if not db_user:
			return await handler(event, data)

		user_status = db_user.get("status")
		logger.debug(f"[BlockedMiddleware] user={user.id}, status={user_status}")

		# Проверяем блокировку
		if user_status == "blocked":
			logger.info(f"[BlockedMiddleware] Заблокированный пользователь {user.id} пытался взаимодействовать")

			# Получаем реальное событие из update
			update = data.get("event_update")
			
			if update and update.message:
				# Обработка сообщения
				msg = update.message
				# Игнорируем команду /start для заблокированных
				if msg.text and msg.text.startswith("/start"):
					return await handler(event, data)

				await msg.answer(
					"🚫 Ваш доступ к StarinaVPN заблокирован.\n\n"
					"Для восстановления доступа обратитесь к администратору: @StarinaVPN_Support"
				)
				# Возвращаем None чтобы остановить выполнение
				return None

			elif update and update.callback_query:
				# Обработка callback query
				callback = update.callback_query
				await callback.answer(
					"🚫 Ваш доступ заблокирован",
					show_alert=True
				)
				# Поднимаем исключение для остановки propagation
				raise CancelHandler()

		return await handler(event, data)

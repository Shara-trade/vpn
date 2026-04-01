"""
Общие кнопки для навигации.
Единые кнопки Назад, Отмена, Закрыть по ТЗ.
"""

from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List


def get_back_button(callback_data: str = "back_to_main") -> InlineKeyboardButton:
    """Кнопка Назад."""
    return InlineKeyboardButton(text="Назад", callback_data=callback_data)


def get_cancel_button() -> InlineKeyboardButton:
    """Кнопка Отмена."""
    return InlineKeyboardButton(text="Отмена", callback_data="cancel_action")


def get_close_button() -> InlineKeyboardButton:
    """Кнопка Закрыть."""
    return InlineKeyboardButton(text="Закрыть", callback_data="close_message")


def get_back_and_close_row(back_callback: str = "back_to_main") -> List[InlineKeyboardButton]:
    """Ряд из кнопок Назад и Закрыть."""
    return [get_back_button(back_callback), get_close_button()]


def get_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой Отмена."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )


def get_back_and_close_keyboard(back_callback: str = "back_to_main") -> InlineKeyboardMarkup:
    """Inline-клавиатура с кнопками Назад и Закрыть."""
    from aiogram.types import InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[get_back_and_close_row(back_callback)])

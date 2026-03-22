"""
Модуль клавиатур.
"""

from keyboards.reply import (
    get_main_keyboard,
    get_admin_keyboard,
    get_cancel_keyboard,
)
from keyboards.inline import (
    get_start_keyboard,
    get_key_keyboard,
    get_profile_keyboard,
    get_back_to_profile_keyboard,
    get_tariffs_keyboard,
    get_purchase_confirm_keyboard,
    get_purchase_success_keyboard,
    get_purchase_error_keyboard,
    get_servers_keyboard,
    get_support_keyboard,
    get_referral_keyboard,
    get_back_to_main_keyboard,
    get_navigation_keyboard,
    get_back_keyboard,
    get_close_keyboard,
    get_back_and_close_keyboard,
    get_regenerate_confirm_keyboard,
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

__all__ = [
    # Reply keyboards
    "get_main_keyboard",
    "get_admin_keyboard",
    "get_cancel_keyboard",
    # User inline keyboards
    "get_start_keyboard",
    "get_key_keyboard",
    "get_profile_keyboard",
    "get_back_to_profile_keyboard",
    "get_tariffs_keyboard",
    "get_purchase_confirm_keyboard",
    "get_purchase_success_keyboard",
    "get_purchase_error_keyboard",
    "get_servers_keyboard",
    "get_support_keyboard",
    "get_referral_keyboard",
    "get_back_to_main_keyboard",
    "get_navigation_keyboard",
    "get_back_keyboard",
    "get_close_keyboard",
    "get_back_and_close_keyboard",
    "get_regenerate_confirm_keyboard",
    # Admin inline keyboards
    "get_user_actions_keyboard",
    "get_admin_balance_confirm_keyboard",
    "get_admin_servers_keyboard",
    "get_server_actions_keyboard",
    "get_admin_mailing_keyboard",
    "get_admin_settings_keyboard",
    "get_admin_tariffs_keyboard",
    "get_admin_cancel_keyboard",
    "get_admin_back_keyboard",
]

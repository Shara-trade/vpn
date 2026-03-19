"""
Конфигурация бота FreakVPN.
"""
import os
from dotenv import load_dotenv

load_dotenv()


# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Trial and referral
DEFAULT_TRIAL_DAYS = int(os.getenv("DEFAULT_TRIAL_DAYS", "3"))
DEFAULT_REFERRAL_BONUS = int(os.getenv("DEFAULT_REFERRAL_BONUS", "5000"))  # в копейках

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "freakvpn.db")

# X-UI settings
XUI_DEFAULT_PORT = int(os.getenv("XUI_DEFAULT_PORT", "54321"))
XUI_DEFAULT_PROTOCOL = os.getenv("XUI_DEFAULT_PROTOCOL", "vless")

# Timezone and logging
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Contacts
PAYMENT_CONTACT = os.getenv("PAYMENT_CONTACT", "@FreakVPN_Shop")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@FreakVPN_Support")

# Bot name
BOT_NAME = "FreakVPN"

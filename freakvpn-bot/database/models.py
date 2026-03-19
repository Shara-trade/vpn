"""
Модели данных для типизации.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Модель пользователя."""
    id: int
    user_id: int
    username: Optional[str]
    full_name: str
    registered_at: datetime
    status: str
    expires_at: Optional[datetime]
    balance: int
    server_id: Optional[int]
    current_key: Optional[str]
    key_uuid: Optional[str]
    referral_code: str
    referred_by: Optional[int]
    referral_earnings: int
    is_admin: bool
    trial_used: bool
    last_activity: Optional[datetime]
    total_traffic: int
    
    @property
    def is_active(self) -> bool:
        """Проверяет, активна ли подписка."""
        if self.status == "blocked":
            return False
        if self.expires_at is None:
            return False
        return self.expires_at > datetime.now()


@dataclass
class Server:
    """Модель сервера."""
    id: int
    name: str
    country_code: str
    domain: str
    ip: str
    api_url: str
    api_username: str
    api_password: str
    port: int
    is_active: bool
    is_trial: bool
    inbound_id: int
    user_count: int
    ping: int
    created_at: datetime
    
    @property
    def flag(self) -> str:
        """Возвращает флаг страны."""
        from utils.helpers import get_flag_emoji
        return get_flag_emoji(self.country_code)
    
    @property
    def display_name(self) -> str:
        """Возвращает отображаемое имя с флагом."""
        return f"{self.flag} {self.name}"


@dataclass
class Tariff:
    """Модель тарифа."""
    id: int
    name: str
    months: int
    price: int
    is_active: bool


@dataclass
class Transaction:
    """Модель транзакции."""
    id: int
    user_id: int
    amount: int
    type: str
    description: Optional[str]
    created_at: datetime
    admin_id: Optional[int]


@dataclass
class Referral:
    """Модель реферала."""
    id: int
    referrer_id: int
    referral_id: int
    bonus_paid: bool
    created_at: datetime


@dataclass
class Mailing:
    """Модель рассылки."""
    id: int
    admin_id: int
    content_type: str
    content: str
    status: str
    total_sent: int
    created_at: datetime
    sent_at: Optional[datetime]

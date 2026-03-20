"""
Модуль базы данных.
"""

from database.db import Database
from database.models import init_db

__all__ = ["Database", "init_db"]

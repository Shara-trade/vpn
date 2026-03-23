"""
Модуль базы данных.
"""

from database.db import Database, db
from database.models import init_db

__all__ = ["Database", "db", "init_db"]

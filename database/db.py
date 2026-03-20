"""
Класс для работы с базой данных SQLite.
"""

import aiosqlite
from typing import Optional, List, Any, Dict
from pathlib import Path

from config import config
from loguru import logger


class Database:
    """Асинхронный класс для работы с SQLite базой данных."""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация подключения к БД.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path or config.DATABASE_PATH
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Создание подключения к базе данных."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            logger.info(f"Подключено к базе данных: {self.db_path}")
    
    async def disconnect(self) -> None:
        """Закрытие подключения к базе данных."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Подключение к базе данных закрыто")
    
    async def execute(
        self, 
        query: str, 
        params: tuple = None,
        fetch: str = None
    ) -> Any:
        """
        Выполнение SQL запроса.
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch: Тип выборки (one, all, val)
            
        Returns:
            Результат запроса
        """
        if self._connection is None:
            await self.connect()
        
        async with self._connection.execute(query, params or ()) as cursor:
            if fetch == "one":
                return await cursor.fetchone()
            elif fetch == "all":
                return await cursor.fetchall()
            elif fetch == "val":
                row = await cursor.fetchone()
                return row[0] if row else None
            else:
                await self._connection.commit()
                return cursor.lastrowid
    
    async def executemany(
        self, 
        query: str, 
        params_list: List[tuple]
    ) -> None:
        """
        Выполнение множества SQL запросов.
        
        Args:
            query: SQL запрос
            params_list: Список параметров
        """
        if self._connection is None:
            await self.connect()
        
        await self._connection.executemany(query, params_list)
        await self._connection.commit()
    
    async def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """
        Получение одной записи.
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Словарь с данными или None
        """
        row = await self.execute(query, params, fetch="one")
        return dict(row) if row else None
    
    async def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Получение всех записей.
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Список словарей с данными
        """
        rows = await self.execute(query, params, fetch="all")
        return [dict(row) for row in rows] if rows else []
    
    async def fetchval(self, query: str, params: tuple = None) -> Any:
        """
        Получение одного значения.
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Значение первого столбца первой строки
        """
        return await self.execute(query, params, fetch="val")


# Глобальный экземпляр базы данных
db = Database()

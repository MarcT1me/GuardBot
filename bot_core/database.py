from abc import ABC, abstractmethod

import aiosqlite

from loguru import logger


class Database(ABC):
    """Абстрактный класс для работы с базой данных"""

    @abstractmethod
    async def connect(self) -> None:
        """Установить соединение с базой данных"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Закрыть соединение с базой данных"""
        pass

    @abstractmethod
    async def execute(self, query: str, *params) -> None:
        """Выполнить SQL-запрос"""
        pass


class SQLiteDatabase(Database):
    def __init__(self, path='guard.db'):
        self.conn = None
        self.path = path

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        logger.success("Database connected")

    async def close(self):
        await self.conn.close()
        logger.info("Database closed")

    async def execute(self, query: str, *params) -> None:
        try:
            async with self.conn.execute(query, params) as cursor:
                if query.strip().upper().startswith("SELECT"):
                    return await cursor.fetchall()
                await self.conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(
                f"Query failed:\n"
                f"query: {query}\n"
                f"exc: {e}"
            )
            raise

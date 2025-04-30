from abc import ABC, abstractmethod


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
    async def execute(self, query: str, *args) -> None:
        """Выполнить SQL-запрос"""
        pass
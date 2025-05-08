from typing import Any
from abc import ABC, abstractmethod

from tortoise import Tortoise
from loguru import logger

from .models import *

TORTOISE_ORM = {
    "connections": {"default": "sqlite://guard_db.sqlite3"},
    "apps": {
        "models": {
            "models": ["bot.database.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}


class Database(ABC):
    @abstractmethod
    async def connect(self, db_url: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class GuardDatabase(Database):
    tortoise: Any
    generate_schemas: Any

    async def connect(self, db_url: str = "sqlite://guard_db.sqlite3") -> None:
        self.tortoise = await Tortoise.init(
            db_url=db_url,
            modules={'models': ['bot.database.models']}
        )
        self.generate_schemas = await Tortoise.generate_schemas()
        logger.success("Database initialized")

    async def close(self) -> None:
        await Tortoise.close_connections()
        logger.info("Database connection closed")

    @staticmethod
    async def get_server(guild_id: int) -> Server | None:
        return await Server.get_or_none(guild_id=guild_id)

    @staticmethod
    async def get_script(server: Server, script_name: str) -> Script:
        return await Script.filter(server=server, name=script_name).first()

    @staticmethod
    async def save_script(server_id: int, name: str, content: str):
        server, _ = await Server.get_or_create(guild_id=server_id)
        await Script.update_or_create(
            server=server,
            name=name,
            defaults={"content": content, "is_active": True}
        )

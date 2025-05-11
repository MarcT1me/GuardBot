from typing import Any
from abc import ABC, abstractmethod

from tortoise import Tortoise
from loguru import logger

from .models import *


class Database(ABC):
    @abstractmethod
    async def connect(self, db_url: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class GuardDatabase(Database):
    tortoise: Any
    generate_schemas: Any

    botdevusers = BotDevUsers

    server = Server
    script = Script
    user_role = UserRole
    template = Template

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
    async def save_server(guild_id: int, name: str) -> Server:
        server, _ = await Server.update_or_create(
            guild_id=guild_id,
            name=name
        )
        return server

    @staticmethod
    async def get_script(server: Server, script_type, script_name: str) -> Script:
        return await Script.filter(server=server, type=script_type, name=script_name).first()

    @staticmethod
    async def save_script(server_id: int, script_type: str, name: str, content: str) -> Script:
        server, _ = await Server.get_or_create(guild_id=server_id)
        script_type = script_type.split(".")
        script, _ = await Script.update_or_create(
            server=server,
            type=script_type[0],
            name=name,
            defaults={"content": content, "language": script_type[1]}
        )
        return script

    @staticmethod
    async def get_template(server: Server, template_name: str) -> Template:
        return await Template.get_or_none(server=server, name=template_name)

    @staticmethod
    async def save_template(server_id: int, name: str, content: str) -> Template:
        server, _ = await Server.get_or_create(guild_id=server_id)
        template, _ = await Template.update_or_create(
            server=server,
            name=name,
            defaults={"content": content}
        )
        return template

    @staticmethod
    async def get_botdevuser(user_id: int) -> BotDevUsers | None:
        return await BotDevUsers.get_or_none(user_id=user_id)

    @staticmethod
    async def save_botdevuser(user_id: int, user_name: str) -> BotDevUsers:
        user, _ = await BotDevUsers.update_or_create(
            user_id=user_id,
            user_name=user_name
        )
        return user

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
    role = Role
    channel = Channel
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

    @classmethod
    async def get_botdevuser(cls, user_id: int) -> BotDevUsers | None:
        return await BotDevUsers.get_or_none(user_id=user_id)

    @classmethod
    async def save_botdevuser(cls, user_id: int, user_name: str) -> BotDevUsers:
        user, _ = await BotDevUsers.update_or_create(
            user_id=user_id,
            user_name=user_name
        )
        return user

    @classmethod
    async def get_server(cls, guild_id: int) -> Server | None:
        return await Server.get_or_none(guild_id=guild_id)

    @classmethod
    async def save_server(cls, guild_id: int, name: str, is_active: bool = False, **additions) -> Server:
        server, _ = await Server.update_or_create(
            guild_id=guild_id,
            name=name,
            is_active=is_active,
            additions=additions
        )
        return server

    @classmethod
    async def get_script(cls, server: Server, script_type, script_name: str) -> Script:
        return await Script.filter(server=server, type=script_type, name=script_name).first()

    @classmethod
    async def save_script(cls, server_id: int, script_type: str, name: str, content: str) -> Script:
        server = await Server.get_or_create(guild_id=server_id)
        script_type = script_type.split(".")
        script = await Script.update_or_create(
            server=server,
            type=script_type[0],
            name=name,
            defaults={"content": content, "language": script_type[1]}
        )
        return script

    @classmethod
    async def get_channel(cls, server: Server, channel_type, name: str) -> Channel:
        return await Channel.get_or_none(server=server, type=channel_type, name=name)

    @classmethod
    async def get_channel_by_id(cls, channel_id):
        return await Channel.get_or_none(id=channel_id)

    @classmethod
    async def save_factory_channel(
            cls, server_id: int, channel_id: int, name: str,
            cooldown: float = 0.0
    ) -> Channel:
        return await cls.save_channel(
            server_id,
            channel_id=channel_id,
            channel_type="voice_factory",
            name=name,

            cooldown=cooldown,
            is_active=True
        )

    @classmethod
    async def save_temp_channel(
            cls, server_id: int, channel_id: int, name: str,
            parent_channel_id: int, owner_id
    ) -> Channel:
        return await cls.save_channel(
            server_id,
            channel_id=channel_id,
            channel_type="temp_voice",
            name=name,

            parent_channel_id=parent_channel_id,
            owner_id=owner_id,
        )

    @classmethod
    async def save_channel(
            cls, server_id: int, channel_id: int, channel_type: str, name: str,
            **additions
    ) -> Channel:
        server = await cls.get_server(server_id)
        channel = await Channel.update_or_create(
            id=channel_id,
            server=server,
            type=channel_type,
            name=name,
            additions=additions
        )
        return channel

    @staticmethod
    async def delete_channel(channel_id: int) -> None:
        await Channel.filter(id=channel_id).delete()

    @classmethod
    async def get_template(cls, server: Server, template_name: str) -> Template:
        return await Template.get_or_none(server=server, name=template_name)

    @classmethod
    async def save_template(cls, server_id: int, name: str, content: str) -> Template:
        server, _ = await Server.get_or_create(guild_id=server_id)
        template, _ = await Template.update_or_create(
            server=server,
            name=name,
            defaults={"content": content}
        )
        return template

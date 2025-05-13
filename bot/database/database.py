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
    async def get_server(cls, guild_id: int) -> Server | None:
        return await Server.get_or_none(guild_id=guild_id)

    @classmethod
    async def save_server(cls, guild_id: int,
                          name: str, is_active: bool = False,
                          **additions) -> Server:
        server, _ = await Server.update_or_create(
            guild_id=guild_id,
            name=name,

            defaults={
                "is_active": is_active,
                "additions": additions
            }
        )
        return server

    @classmethod
    async def get_user(cls, user_id: int) -> User | None:
        return await User.get_or_none(id=user_id)

    @classmethod
    async def save_botdevuser(cls, server_id: int,
                              user_id: int, user_name: str, user_types: str = "") -> User:
        user = await cls.get_user(user_id)
        if user: user_types += "\\" + user.types
        user = await cls.save_user(
            server_id=server_id,
            user_id=user_id,
            user_types=user_types + "\\" + "botdev",
            user_name=user_name,
        )
        return user

    @classmethod
    async def save_user(cls, server_id: int,
                        user_id: int, user_name: str, user_types: str = "",
                        **additions) -> User:
        user, _ = await User.update_or_create(
            id=user_id,
            server=await cls.get_server(server_id),

            name=user_name,

            defaults={
                "user_types": user_types,
                "additions": additions
            },
        )
        return user

    @classmethod
    async def get_script(cls, server: Server, script_type, script_name: str) -> Script:
        return await Script.get_or_none(server=server, type=script_type, name=script_name)

    @classmethod
    async def get_script_by_id(cls, script_id: int) -> Script:
        return await Script.get_or_none(id=script_id)

    @classmethod
    async def save_script(cls, server_id: int,
                          script_type: str, name: str,
                          content: str, is_active: bool = False,
                          **additions) -> Script:
        server = await cls.get_server(guild_id=server_id)
        script_type = script_type.split(".")
        script, _ = await Script.update_or_create(
            server=server,

            type=script_type[0],
            name=name,

            language=script_type[1],
            defaults={
                "content": content,
                "is_active": is_active,
                "additions": additions
            }
        )
        return script

    @classmethod
    async def get_channel(cls, server: Server, channel_type, name: str) -> Channel:
        return await Channel.get_or_none(server=server, type=channel_type, name=name)

    @classmethod
    async def get_channel_by_id(cls, channel_id):
        return await Channel.get_or_none(id=channel_id)

    @classmethod
    async def save_factory_channel(cls, server_id: int,
                                   channel_id: int,
                                   cooldown: float = 0.0, is_active=False) -> Channel:
        return await cls.save_channel(
            server_id,
            channel_id,
            "voice_factory",

            cooldown=cooldown,
            is_active=is_active
        )

    @classmethod
    async def save_temp_channel(cls, server_id: int,
                                channel_id: int,
                                parent_channel_id: int, owner_id) -> Channel:
        return await cls.save_channel(
            server_id,
            channel_id,
            "temp_voice",

            parent_channel_id=parent_channel_id,
            owner_id=owner_id,
        )

    @classmethod
    async def save_channel(cls, server_id: int,
                           channel_id: int, channel_type: str,
                           **additions) -> Channel:
        server = await cls.get_server(server_id)
        channel, _ = await Channel.update_or_create(
            id=channel_id,
            server=server,
            type=channel_type,
            defaults={
                "additions": additions
            }
        )
        return channel

    @staticmethod
    async def delete_channel(channel_id: int) -> None:
        await Channel.filter(id=channel_id).delete()

    @classmethod
    async def get_template(cls, server: Server, template_name: str) -> Template:
        return await Template.get_or_none(server=server, name=template_name)

    @classmethod
    async def get_template_by_id(cls, template_id: int) -> Template:
        return await Template.get_or_none(id=template_id)

    @classmethod
    async def save_template(cls, server_id: int,
                            name: str,
                            content: str, is_active: bool = False) -> Template:
        server = await cls.get_server(guild_id=server_id)
        template, _ = await Template.update_or_create(
            server=server,
            name=name,
            defaults={
                "content": content,
                "is_active": is_active
            },
        )
        return template

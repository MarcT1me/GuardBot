import asyncio
from typing import Any
from abc import abstractmethod

import discord
from discord.ext import commands
from loguru import logger

import bot
from bot import GuardBot, GuardDatabase


class _SafeDiscordApi:
    Interaction = discord.Interaction
    Message = discord.Message
    Member = discord.Member
    Guild = discord.Guild
    Role = discord.Role

    TextChannel = discord.TextChannel
    VoiceChannel = discord.VoiceChannel
    StageChannel = discord.StageChannel

    SelectOption = discord.SelectOption

    VoiceState = discord.VoiceState
    Permissions = discord.Permissions

    Colour = discord.Colour
    Asset = discord.Asset
    CustomActivity = discord.CustomActivity

    AllowedMentions = discord.AllowedMentions
    File = discord.File
    Embed = discord.Embed


class _SafeDataBase:
    user: GuardDatabase.user = None
    script: GuardDatabase.script = None
    role: GuardDatabase.role = None
    channel: GuardDatabase.channel = None
    template: GuardDatabase.template = None

    def __init__(self, server: GuardDatabase.server):
        self.__server = server

    async def init(self, _id: int, **kwargs):
        self.__server = await GuardDatabase.save_server(
            guild_id=_id,
            **kwargs
        )

    async def dispose(self, _id: int):
        guild = GuardBot.instance.get_guild(_id)
        await GuardBot.instance.voice_state_manager.disconnect_guild(guild)
        for channel in self.get_channels(channel_type="voice_factory"):
            await channel.delete()
        for user in guild.members:
            await self.remove_user(user_id=user.id)
        await GuardDatabase.remove_server(
            guild_id=_id
        )

    def server_addition(self, name: str) -> Any:
        return self.__server.additions.get(name)

    async def save_server_addition(self, name: str, value: Any):
        self.__server.additions[name] = value
        await self.__server.save()

    async def get_user(self, *, user_id: int) -> GuardDatabase.user | None:
        return await GuardDatabase.get_user(server=self.__server, user_id=user_id)

    async def save_user(self, *, user_id: int,
                        **additions) -> GuardDatabase.user:
        return await GuardDatabase.save_user(guild_id=self.__server.guild_id, user_id=user_id, **additions)

    async def remove_user(self, *, user_id: int) -> None:
        await GuardDatabase.remove_user(server=self.__server, user_id=user_id)

    async def get_channels(self, *, channel_type) -> list[GuardDatabase.channel]:
        return await GuardDatabase.get_channels(server=self.__server, channel_type=channel_type)

    async def get_channel_by_id(self, *, channel_id) -> GuardDatabase.channel | None:
        db_channel = await GuardDatabase.get_channel_by_id(channel_id=channel_id)
        if db_channel:
            channel_guild_id = (await db_channel.server.values("guild_id"))["guild_id"]
            return db_channel if channel_guild_id == self.__server.guild_id else None
        return None

    async def save_factory_channel(self, *, channel_id: int,
                                   cooldown: float = 0.0, is_active=False) -> GuardDatabase.channel:
        return await GuardDatabase.save_factory_channel(
            server_id=self.__server.guild_id,
            channel_id=channel_id,

            cooldown=cooldown,
            is_active=is_active,
            last_updated_channel=None,
            last_updating_time=0
        )

    async def save_temp_channel(self, *, channel_id: int,
                                parent_channel_id: int, owner_id) -> GuardDatabase.channel:
        return await GuardDatabase.save_temp_channel(
            server_id=self.__server.guild_id,
            channel_id=channel_id,

            parent_channel_id=parent_channel_id,
            owner_id=owner_id,
        )

    async def save_channel(self, *, channel_id: int, channel_type: str,
                           **additions) -> GuardDatabase.channel:
        return await GuardDatabase.save_channel(
            server_id=self.__server.guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
            **additions
        )

    async def delete_channel(self, *, channel_id: int) -> None:
        db_channel = await GuardDatabase.get_channel_by_id(channel_id=channel_id)
        if db_channel:
            channel_guild_id = (await db_channel.server.values("guild_id"))["guild_id"]
            if channel_guild_id == self.__server.guild_id:
                await GuardDatabase.delete_channel(channel_id=channel_id)

    async def get_template(self, *, template_name: str) -> GuardDatabase.template | None:
        return await GuardDatabase.get_template(server=self.__server, template_name=template_name)

    async def get_template_by_id(self, *, template_id: int) -> GuardDatabase.template | None:
        db_template = await GuardDatabase.get_template_by_id(template_id=template_id)
        if db_template:
            template_guild_id = (await db_template.server.values("guild_id"))["guild_id"]
            return db_template if db_template and template_guild_id == self.__server.guild_id else None
        return None

    async def save_template(self, *, name: str, content: str, is_active: bool = False) -> GuardDatabase.template:
        return await GuardDatabase.save_template(
            server_id=self.__server.guild_id,
            name=name,
            content=content,
            is_active=is_active
        )


class _ScriptGuild:
    def __init__(self, engine: 'bot.script_engine.ScriptEngine', db: _SafeDataBase,
                 guild: discord.Guild = None):
        self.engine: bot.script_engine.ScriptEngine = engine

        guild = guild

        if guild:
            self.id: int = guild.id
            self.name: str = guild.name
            self.members: list[discord.Member] = getattr(guild, "members")
        else:
            self.id: int = None
            self.name: str = None
            self.members: list[discord.Member] = []
        self.db: _SafeDataBase = db

    def set_async_event(self, name: str, event: asyncio.Event) -> None:
        bot.script_engine.ScriptEngine.async_events.setdefault(self.id, {})[name] = event

    def get_async_event(self, name: str) -> asyncio.Event:
        return bot.script_engine.ScriptEngine.async_events.setdefault(self.id, {}).get(name)


class SafeBot:
    cog_dictionary: dict[int, commands.Cog] = {}

    def __init__(self, bot_user: discord.User, script_guild: _ScriptGuild):
        self.name = bot_user.name
        self.global_name = bot_user.global_name
        self.id: int = bot_user.id
        self.mention: str = getattr(bot_user, "mention")
        self.color: discord.Colour = getattr(bot_user, "color")
        self.banner: discord.Asset = getattr(bot_user, "banner")
        self.avatar: discord.Asset = getattr(bot_user, "avatar")
        self.guild = script_guild

    async def setup_guild_only_cog(self, cog: commands.Cog):
        _bot = GuardBot.instance
        guild = _bot.get_guild(self.guild.id)
        if cog.__cog_name__ in _bot.cogs:
            await _bot.remove_cog(cog.__cog_name__, guild=guild)
        await _bot.add_cog(cog, override=True, guild=guild)
        SafeBot.cog_dictionary[guild.id] = cog
        await _bot.tree.sync(guild=guild)

    err_handler = GuardBot.error_handler
    has_permission = GuardBot.has_permission
    normalize_response_size = GuardBot.normalize_response_size
    normalized_reason = GuardBot.normalized_reason
    normalize_response_reason = GuardBot.normalize_response_reason

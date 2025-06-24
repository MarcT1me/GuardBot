import discord as _discord
from discord.ext.commands import (
    Cog,
    Group,
    GroupCog
)
import discord.app_commands as _app_commands
from discord import ui

import datetime
import asyncio
import random
import json

from typing import (
    Callable, Optional, Any,
    Iterable as _Iterable,
    Iterator as _Iterator,
)

from loguru import logger
from enum import Enum, auto

from bot import (
    GuardBot as _GuardBot,
    GuardDatabase as _GuardDatabase
)

from abc import ABC, abstractmethod


class discord:
    Interaction = _discord.Interaction
    Message = _discord.Message
    Member = _discord.Member
    Guild = _discord.Guild
    Role = _discord.Role

    TextChannel = _discord.TextChannel
    VoiceChannel = _discord.VoiceChannel
    StageChannel = _discord.StageChannel

    SelectOption = _discord.SelectOption

    VoiceState = _discord.VoiceState
    Permissions = _discord.Permissions
    TextStyle = _discord.TextStyle

    Colour = _discord.Colour
    Asset = _discord.Asset
    CustomActivity = _discord.CustomActivity

    AllowedMentions = _discord.AllowedMentions
    File = _discord.File
    Embed = _discord.Embed


class app_commands:
    command = _app_commands.command
    describe = _app_commands.describe


class ScriptDatabase:
    user: _GuardDatabase.user
    script: _GuardDatabase.script
    role: _GuardDatabase.role
    channel: _GuardDatabase.channel
    template: _GuardDatabase.template

    async def init(self, _id: int, **kwargs): pass

    async def dispose(self, _id: int): pass

    def server_addition(self, name: str) -> Any: pass

    def save_server_addition(self, name: str, value: Any): pass

    async def get_user(self, *, user_id: int) -> _GuardDatabase.user | None: pass

    async def save_user(self, *, user_id: int,
                        **additions) -> _GuardDatabase.user: pass

    async def remove_user(self, *, user_id: int) -> None: pass

    async def get_channels(self, *, channel_type) -> list[_GuardDatabase.channel]: pass

    async def get_channel_by_id(self, *, channel_id) -> _GuardDatabase.channel | None: pass

    async def save_factory_channel(self, *, channel_id: int,
                                   cooldown: float = 0.0, is_active=False) -> _GuardDatabase.channel: pass

    async def save_temp_channel(self, *, channel_id: int,
                                parent_channel_id: int, owner_id) -> _GuardDatabase.channel: pass

    async def save_channel(self, *, channel_id: int, channel_type: str,
                           **additions) -> _GuardDatabase.channel: pass

    async def delete_channel(self, *, channel_id: int) -> None: pass

    async def get_template(self, *, template_name: str) -> _GuardDatabase.template | None: pass

    async def get_template_by_id(self, *, template_id: int) -> _GuardDatabase.template | None: pass

    async def save_template(self, *, name: str, content: str, is_active: bool = False) -> _GuardDatabase.template: pass


class ScriptGuild:
    id: int
    name: str
    members: list[discord.Member]
    db: ScriptDatabase

    def set_async_event(self, name: str, event: asyncio.Event) -> None: pass

    def get_async_event(self, name: str) -> asyncio.Event: pass


class Bot:
    name: str
    id: int
    global_name: str
    mention: str
    color: discord.Colour
    banner: discord.Asset
    avatar: discord.Asset
    guild: ScriptGuild
    loop: asyncio.EventLoop

    async def setup_guild_only_cog(self, cog: Cog): pass

    err_handler = _GuardBot.error_handler
    has_permission = _GuardBot.has_permission
    normalize_response_size = _GuardBot.normalize_response_size
    normalized_reason = _GuardBot.normalized_reason
    normalize_response_reason = _GuardBot.normalize_response_reason


def iterate[T](expr: _Iterable[T]) -> _Iterator[tuple[int, T]]: pass


def calculate(expr: str) -> float: pass


def include(script_name: str, as_name: Optional[str] = None) -> Any: pass

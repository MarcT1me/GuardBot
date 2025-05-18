import discord as _discord
from discord.ext.commands import Cog
import discord.app_commands as app_commands

import datetime
import asyncio
import random

from typing import (
    Callable, Optional, Any,
    Iterable as _Iterable,
    Iterator as _Iterator,
)
from loguru import logger

from bot import GuardBot


class discord:
    Interaction = _discord.Interaction
    Message = _discord.Message
    Member = _discord.Member
    Guild = _discord.Guild
    Role = _discord.Role

    TextChannel = _discord.TextChannel
    VoiceChannel = _discord.VoiceChannel
    StageChannel = _discord.StageChannel
    VoiceState = _discord.VoiceState

    Colour = _discord.Colour
    Asset = _discord.Asset

    AllowedMentions = _discord.AllowedMentions
    File = _discord.File
    Embed = _discord.Embed


err_handler = GuardBot.error_handler
has_permission = GuardBot.has_permission
normalize_response_size = GuardBot.normalize_response_size
normalized_reason = GuardBot.normalized_reason
normalize_response_reason = GuardBot.normalize_response_reason

guild_id: int
include: Callable[[str, Optional[str]], None]
calculate: Callable[[str], float]
async_events: dict[str, asyncio.Event]


def iterate[T](expr: _Iterable[T]) -> _Iterator[tuple[int, T]]: pass


def calculate(expr: str) -> float: pass


def include(script_name: str, as_name: str = None) -> None: pass


def set_async_event(name: str, event: asyncio.Event) -> None: pass


def get_async_event(name: str) -> asyncio.Event: pass

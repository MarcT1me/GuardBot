import discord
from discord.ext.commands import Cog
import discord.app_commands as app_commands

import datetime
import asyncio
import random

from typing import Callable, Optional, Any
from loguru import logger

from bot import GuardBot

err_handler = GuardBot.error_handler
has_permission = GuardBot.has_permission
normalize_response_size = GuardBot.normalize_response_size
normalized_reason = GuardBot.normalized_reason
normalize_response_reason = GuardBot.normalize_response_reason

guild_id: int
include: Callable[[str, Optional[str]], None]
calculate: Callable[[str], float]

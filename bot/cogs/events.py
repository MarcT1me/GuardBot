from typing import Any

import discord
from discord.ext import commands

from loguru import logger

from bot.bot import GuardBot


class EventCog(commands.Cog):
    """Обработчик событий бота"""

    def __init__(self, bot: GuardBot):
        self.bot = bot

    async def _get_event_script_name(self, guild, event_name: str) -> str:
        if not guild:
            return event_name

        server, _ = await self.bot.db.get_server(guild.id)
        return server.scripts.get(event_name, event_name)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        script_name = (await self._get_event_script_name(member.guild, "on_member_join"))[1]

        await self.bot.script_eng.execute(
            script_name,
            member=member
        )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        script_name = (await self._get_event_script_name(msg.guild, "on_message"))[1]

        await self.bot.script_eng.execute(
            script_name,
            msg=msg
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ EventCog loading")
    await bot.add_cog(EventCog(bot))

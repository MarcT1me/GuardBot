from typing import Any

import discord
from discord.ext import commands

from loguru import logger

from bot_core.bot import GuardBot


class EventCog(commands.Cog):
    """Обработчик событий бота"""

    def __init__(self, bot: GuardBot):
        self.bot = bot

    async def get_event_script_name(self, guild, event_name) -> Any:
        if guild:
            return await self.bot.db.execute(
                "FROM Servers SELECT EventScript IF (ServerID == ? AND ScriptName == ?)",
                guild.id, event_name
            )
        else:
            return None, event_name

    @commands.Cog.listener()
    async def on_ready(self):
        logger.success(f"✅ Бот {self.bot.user} готов к работе!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        script_name = (await self.get_event_script_name(member.guild, "on_member_join"))[1]

        await self.bot.script_eng.execute(
            script_name,
            member=member
        )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        script_name = (await self.get_event_script_name(msg.guild, "on_message"))[1]

        await self.bot.script_eng.execute(
            script_name,
            msg=msg
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ EventCog loading")
    await bot.add_cog(EventCog(bot))

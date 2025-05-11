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
            return event_name, None

        server = await self.bot.db.get_server(guild.id)
        return await self.bot.db.get_script(
            server=server, script_type="Python-default-event", script_name=event_name
        ), guild.id

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.script_eng.execute(
            "on_guild_join",
            None,
            guild=guild
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        script_name, guild_id = await self._get_event_script_name(None, "on_member_join")

        await self.bot.script_eng.execute(
            script_name,
            None,
            member=member
        )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        script_name, guild_id = await self._get_event_script_name(None, "on_message")

        await self.bot.script_eng.execute(
            script_name,
            None,
            msg=msg
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ EventCog loading")
    await bot.add_cog(EventCog(bot))

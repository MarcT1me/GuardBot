import discord
from discord.ext import commands

from loguru import logger

from bot.bot import GuardBot, GuardDatabase


class EventCog(commands.Cog):
    """Обработчик событий бота"""

    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

    async def _get_event_script(self, guild, event_name: str) -> tuple[GuardDatabase.script, int]:
        return await self.bot.script_eng.get_event_script(guild, event_name)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        script_name, guild_id = await self._get_event_script(None, "on_member_join")
        await self.bot.script_eng.execute(
            script_name, guild.id,
            guild=guild
        )

        script_name, guild_id = await self._get_event_script(None, "on_ready")
        await self.bot.script_eng.execute(
            script_name, guild.id,
            guild=guild
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        script_name, guild_id = await self._get_event_script(None, "on_member_join")
        await self.bot.script_eng.execute(
            script_name, member.guild.id,
            member=member
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        script_name, guild_id = await self._get_event_script(None, "on_member_remove")
        await self.bot.script_eng.execute(
            script_name, member.guild.id,
            member=member
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Проверяем, что pending изменился с True на False
        if before.pending and not after.pending:
            await self.on_member_registered(after)
        else:
            script_name, guild_id = await self._get_event_script(None, "on_member_update")
            await self.bot.script_eng.execute(
                script_name, after.guild.id if after.guild else before.guild.id,
                before=before,
                after=after
            )

    async def on_member_registered(self, member: discord.Member):
        script_name, guild_id = await self._get_event_script(None, "on_member_registered")
        await self.bot.script_eng.execute(
            script_name, member.guild.id,
            member=member
        )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        script_name, guild_id = await self._get_event_script(None, "on_message")
        await self.bot.script_eng.execute(
            script_name, msg.guild.id if msg.guild else None,
            msg=msg
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState, after: discord.VoiceState):
        script_name, guild_id = await self._get_event_script(None, "on_voice_state_update")
        await self.bot.script_eng.execute(
            script_name, member.guild.id,
            member=member,
            before=before,
            after=after
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ EventCog loading")
    await bot.add_cog(EventCog(bot))

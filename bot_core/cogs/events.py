import discord
from discord.ext import commands

from bot_core.bot import GuardBot


class EventCog(commands.Cog):
    """Обработчик событий бота"""

    def __init__(self, bot: GuardBot):
        self.bot = bot

    def get_event_script_name(self, guild, event_name):
        return self.bot.db.execute(
            "FROM Servers SELECT EventScript IF (ServerID == ? AND ScriptName == ?)",
            guild.id, event_name
        )

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Бот {self.bot.user} готов к работе!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        script_name = self.get_event_script_name(member.guild, "on_member_join")

        await self.bot.script_engine.execute(
            script_name,
            member=member
        )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        script_name = self.get_event_script_name(msg.guild, "on_member_join")

        await self.bot.script_engine.execute(
            script_name,
            msg=msg
        )

        print(msg.author.name + ": " + msg.content)


async def setup(bot: commands.Bot):
    print(f"⚙️ EventCog loading")
    await bot.add_cog(EventCog(bot))

import discord
from discord.ext import commands


class EventCog(commands.Cog):
    """Обработчик событий бота"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Бот {self.bot.user} готов к работе!")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel:
            await channel.send(f"➕ Добро пожаловать, {member.mention}!")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        print(msg.author.name + ": " + msg.content)


async def setup(bot: commands.Bot):
    print(f"⚙️ EventCog loading")
    await bot.add_cog(EventCog(bot))

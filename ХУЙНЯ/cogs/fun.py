import discord
from discord.ext import commands


class FunCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.counter = 0  # Пример состояния

    @commands.command(name="hello")
    async def hello_cmd(self, ctx: commands.Context):
        await ctx.send(f"Привет, {ctx.author.mention}! я - дискорд бот-хуила, я ебал себя, почему я такой нищенский")

    @commands.hybrid_command(name="meme")
    async def meme_slash(self, interaction: discord.Interaction):
        """Получить случайный мем"""
        await interaction.response.send_message("ИДИ НА ХУЙ ДИСКОРД БОТ БЛЯТЬ!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if "бот" in message.content.lower():
            self.counter += 1
            await message.add_reaction("🤖")


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))

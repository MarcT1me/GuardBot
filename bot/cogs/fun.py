import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from bot.bot import GuardBot


class FunCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

    @app_commands.command(name="ping", description="checking on bot working")
    @GuardBot.error_handler()
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(  # type: ignore
            "Pong!"
        )

    @app_commands.command(name="nping", description="Check network latency")
    @GuardBot.error_handler()
    async def nping(self, interaction: discord.Interaction):
        # Получаем задержку в миллисекундах
        latency = round(self.bot.latency * 1000, 2)
        await interaction.response.send_message(  # type: ignore
            f"🏓 Network ping: {latency}ms"
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ FunCog loading")
    await bot.add_cog(FunCog(bot))

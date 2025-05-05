import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from bot_core.bot import try_execute, GuardBot


class FunCog(commands.Cog):
    @app_commands.command(name="ping", description="...")
    @try_execute
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(  # type: ignore
            "Pong!"
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ FunCog loading")
    await bot.add_cog(FunCog(bot))

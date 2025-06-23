import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from bot import GuardBot, script_engine


class SettingsCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

    @app_commands.command(
        name="settings",
        description="настройки"
    )
    @app_commands.guild_only
    async def settings(self, interaction: discord.Interaction):
        on_ready_script: commands.Cog = script_engine.scripts.SafeBot.cog_dictionary.get(interaction.guild_id)

        if on_ready_script:
            return await interaction.response.send_message(  # type: ignore
                "**Settings panel**\n",
                view=on_ready_script.get_settings_view(interaction),
                ephemeral=True
            )
        return await interaction.response.send_message(  # type: ignore
            "**NOT ALLOW SETTINGS PANEL**\n",
            ephemeral=True
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ LoggingCog loading")
    await bot.add_cog(
        SettingsCog(
            bot
        )
    )

from loguru import logger

import discord
from discord import app_commands
from discord.ext import commands

from bot import GuardBot


class EliteGuardionCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

        logger.success("Setup guild only cog")

    @app_commands.command(name="test_cmd", description="command only for EliteGuardion")
    async def test_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.channel.send(
            f"ХУЙ, {member.mention}",
            allowed_mentions=discord.AllowedMentions(users=False)
        )


async def main(*, bot: GuardBot, interaction: discord.Guild | discord.Interaction):
    guild = interaction.guild
    await interaction.channel.send(f"On Ready: {bot.user.name}, {guild.name}")
    if "EliteGuardionCog" in bot.cogs:
        await bot.remove_cog("EliteGuardionCog", guild=guild)
    await bot.add_cog(EliteGuardionCog(bot), guild=guild)
    await bot.tree.sync(guild=guild)
    return None

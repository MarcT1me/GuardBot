import discord
from loguru import logger

from bot import GuardBot


async def main(*, bot: GuardBot, interaction: discord.Interaction):
    guild = interaction.guild
    await bot.db.save_server(
        guild.id,
        guild.name,
        is_active=True,
        voice_channel_announce=1371207588045262868
    )

    await interaction.channel.send(f"Guild: {guild.name} added to DataBase")

    await bot.script_eng.execute("add_bot_dev_users", None, interaction=interaction)
    await bot.script_eng.execute("add_template_to_db", None, interaction=interaction)
    await bot.script_eng.execute("add_voice_factory", None, interaction=interaction, channel_id=1371185726502338610)

    logger.success(f"init bot deps for {guild.name}")

import discord
from loguru import logger

from bot import GuardBot


async def main(*, bot: GuardBot, guild: discord.Guild):
    class FakeInteraction:
        def __init__(self):
            self.guild = guild
            self.channel = guild.system_channel

    try:
        await bot.script_eng.execute("add_guild_to_db", None, interaction=FakeInteraction())
    except Exception as e:
        await guild.system_channel.send(f"Error - cant init deps for server {guild}: {e}")
        logger.exception(f"Error - cant init deps for server {guild}")

    logger.success(f"init bot deps for {guild}")

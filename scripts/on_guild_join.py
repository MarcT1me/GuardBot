import discord
from loguru import logger

from bot import GuardBot


async def main(*, bot: GuardBot, guild: discord.Guild):
    bot.script_eng.execute("add_guild_to_db", None)
    logger.success(f"init bot deps for {guild.name}")

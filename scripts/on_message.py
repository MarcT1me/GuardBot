import discord
from loguru import logger
from bot import GuardBot


async def main(bot: GuardBot, *, msg: discord.Message):
    logger.info(
        msg.author.name +
        (f" (server: {msg.guild.name})" if msg.guild else "") +
        ":\n" + msg.content
    )
    return None

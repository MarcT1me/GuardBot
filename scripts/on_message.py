import discord
from loguru import logger

import bot


async def main(_: bot.GuardBot, *, msg: discord.Message):
    logger.info(msg.author.name + ":\n" + msg.content)
    return None

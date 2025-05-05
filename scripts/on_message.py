import discord
from loguru import logger

import bot_core


async def main(_: bot_core.GuardBot, *, msg: discord.Message):
    logger.info(msg.author.name + ":\n" + msg.content)
    return None

import discord
from loguru import logger

from bot import GuardBot


async def main(*, bot: GuardBot, msg: discord.Message):
    ret = msg.author.name + (
        f", server: `{msg.guild.name}`, channel: `{msg.channel.name}`"
        if msg.guild else
        ""
    )
    if msg.content:
        ret += "\ncontent: " + msg.content
    for embed in msg.embeds:
        ret += "\nembed: " + embed.title
    logger.info(
        ret
    )
    return None

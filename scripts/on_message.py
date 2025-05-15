from bot.script_evs import *


async def main(*, bot: GuardBot, msg: discord.Message):
    ret = msg.author.name + (
        f", server: `{msg.guild.name}`, channel: `{msg.channel.name}`"
        if msg.guild else
        ""
    )
    if msg.content:
        ret += "\ncontent: " + msg.content
    for embed in msg.embeds:
        ret += "\nembed:\ntitle: " + embed.title if embed.title else "None"
        ret += "\ndescription: " + embed.description if embed.description else "None"
    logger.info(
        ret
    )
    return None

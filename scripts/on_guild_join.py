from bot.script_evs import *

import add_guild_to_db


async def main(*, bot: Bot, guild: discord.Guild):
    class FakeInteraction:
        def __init__(self):
            self.guild = guild
            self.channel = guild.system_channel

    try:
        await add_guild_to_db.main(bot=bot, interaction=FakeInteraction())
    except Exception as e:
        await guild.system_channel.send(f"Error - cant init deps for server {guild}: {e}")
        logger.exception(f"Error - cant init deps for server {guild}")

    logger.success(f"init bot deps for {guild}")

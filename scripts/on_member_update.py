from bot.script_env import *

async def main(*, bot: Bot, before: discord.Member, after: discord.Member):
    logger.info(
        f"{bot.guild.name} on member update: {before.name}"
    )

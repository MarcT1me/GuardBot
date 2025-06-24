from bot.script_env import *


async def main(*, bot: Bot, before: discord.Member, after: discord.Member):
    if after.guild is None:
        if after.id == bot.id:
            await bot.guild.db.dispose(before.guild.id)
            logger.info(
                f"LEFT FROM {bot.guild.name}"
            )
        else:
            await bot.guild.db.remove_user(user_id=before.id)
            logger.info(
                f"{before.name} has left from {bot.guild.name}"
            )
        return None
    logger.info(
        f"{bot.guild.name} on member update: {before.name}"
    )
    return None

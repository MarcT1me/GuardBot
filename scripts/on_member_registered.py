from bot.script_evs import *


async def main(*, bot: Bot, member: discord.Message):
    event = bot.guild.get_async_event(f"on_member_{member.id}")
    logger.info(f"on_member_{member.id} " + str(event))
    if event:
        event.set()
        logger.success(f"User registered on guild {member.guild}")

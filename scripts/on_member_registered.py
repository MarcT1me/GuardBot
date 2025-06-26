from bot.script_env import *


async def main(*, bot: Bot, member: discord.Member = None, member_id: int = None, **kwargs):
    if member_id is not None:
        for member in bot.guild.members:
            if member.id == member_id:
                break

    if member.bot: return

    event = bot.guild.get_async_event(f"on_member_{member.id}")
    logger.info(f"on_member_registered_{member.id} " + str(event))
    if event:
        event.set()
        logger.success(f"User registered on guild {member.guild}")

from bot.script_evs import *


async def main(*, bot: GuardBot, member: discord.Message):
    if event := async_events.get(f"on_member_{member.id}"):
        event.set()
        logger.success(f"User registered on guild {member.guild}")

from .bot import GuardBot
from .database import *
from bot.cogs.script_engine import *
from .cogs import voice_core
from os import getenv


def main():
    guard_bot = GuardBot(
        database=GuardDatabase()
    )

    guard_bot.run(getenv("GUARD_BOT_API_KEY"))

    return GuardBot.is_restart

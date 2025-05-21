from .bot import GuardBot
from .database import *
from .script_engine import *
from . import voice_core
from os import getenv


def main():
    guard_bot = GuardBot(
        database=GuardDatabase()
    )

    guard_bot.run(getenv("GUARD_BOT_API_KEY"))

    return GuardBot.is_restart

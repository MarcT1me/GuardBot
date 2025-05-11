from .bot import GuardBot
from .database import *
from os import getenv


def main():
    guard_bot = GuardBot(
        database=GuardDatabase()
    )

    guard_bot.run(getenv("GUARD_BOT_API_KEY"))

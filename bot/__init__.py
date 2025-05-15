from .bot import GuardBot
from .database import *
from os import getenv


def main():
    guard_bot = GuardBot(
        database=GuardDatabase()
    )

    try:
        guard_bot.run(getenv("GUARD_BOT_API_KEY"))
    finally:
        guard_bot.loop.run_until_complete(guard_bot.close())

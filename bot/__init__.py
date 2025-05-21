from .bot import GuardBot
from .database import *
from bot.cogs.script_engine import *
from .cogs import voice_core

from dotenv import load_dotenv
import os


def main():
    guard_bot = GuardBot(
        database=GuardDatabase()
    )

    load_dotenv()
    guard_bot.run(os.getenv("GUARD_BOT_API_KEY"))

    return GuardBot.is_restart

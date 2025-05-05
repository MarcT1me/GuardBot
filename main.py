from os import getenv

from discord import Intents

from bot_core import SQLiteDatabase, GuardBot


class GuardDatabase(SQLiteDatabase):
    pass


def main():
    intents = Intents.default()
    intents.members = True
    intents.message_content = True

    bot = GuardBot(
        database=GuardDatabase(),
        command_prefix="/",
        intents=intents
    )

    bot.run(getenv("GUARD_BOT_API_KEY"))


if __name__ == "__main__":
    main()

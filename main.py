from os import getenv

from discord import Intents

from bot_core import GuardBot
from bot_core import Database


class MockDatabase(Database):
    async def connect(self):
        print("🔌 Mock DB connected")

    async def close(self):
        print("🔌 Mock DB closed")

    async def execute(self, query: str, *args):
        print(f"📝 Executing: {query}")


def main():
    intents = Intents.default()
    intents.members = True
    intents.message_content = True

    bot = GuardBot(
        database=MockDatabase(),
        command_prefix="/",
        intents=intents
    )

    bot.run(getenv("GUARD_BOT_API_KEY"))


if __name__ == "__main__":
    main()

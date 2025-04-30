import os
import discord
from discord.ext import commands
import asyncio

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


async def main():
    await bot.load_extension("cogs.fun")
    await bot.start(os.getenv("GUARD_BOT_API_KEY"))


if __name__ == "__main__":
    asyncio.run(main())

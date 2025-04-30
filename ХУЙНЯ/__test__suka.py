import os
import discord
from discord.ext import commands
from typing import Any


class BotCommandMixin:
    """Миксин для команд с разделением типов"""

    def _add_core_commands(self: commands.Bot) -> None:
        # Гибридная команда (работает через / и префикс)
        @self.hybrid_command(name="ping", description="Проверка работоспособности")
        async def hybrid_ping(ctx: commands.Context):
            await ctx.send("Pong! (Hybrid)")

        # Обычная текстовая команда (только через префикс)
        @self.command(name="legacy_ping")
        async def prefix_ping(ctx: commands.Context):
            await ctx.send("Pong! (Prefix)")


class EventHandler:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def on_ready(self) -> None:
        print(f"Бот {self.bot.user} запущен!")
        await self.bot.tree.sync()  # Синхронизация только для slash/hybrid команд


class MyBot(BotCommandMixin, commands.Bot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True  # Обязательно для текстовых команд!

        super().__init__(
            command_prefix="!",
            intents=intents,
            *args,
            **kwargs
        )
        self.event_handler = EventHandler(self)
        self._setup()

    def _setup(self) -> None:
        self._add_core_commands()
        self._register_events()

    def _register_events(self) -> None:
        self.add_listener(self.event_handler.on_ready)


if __name__ == "__main__":
    guard_bot = MyBot()
    guard_bot.run(os.getenv("GUARD_BOT_API_KEY"))
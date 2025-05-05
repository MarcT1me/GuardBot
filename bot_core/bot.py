from functools import wraps

import discord
from discord.ext import commands
from pathlib import Path
from .database import Database
from .script_engine import ScriptEngine


def try_execute(func):
    @wraps(func)  # Сохраняем метаданные оригинальной функции
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        try:
            return await func(self, interaction, *args, **kwargs)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Недостаточно прав для выполнения!",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error: {e}")
            await interaction.response.send_message(
                "❌ Неизвестная ошибка при выполнении!",
                ephemeral=True
            )

    return wrapper


class GuardBot(commands.Bot):
    def __init__(self, database: Database, script_engine: ScriptEngine,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = database
        self.script_engine = script_engine

    async def setup_hook(self) -> None:
        """Асинхронная загрузка когов при запуске"""
        await self._load_cogs()
        await self.tree.sync()

    async def _load_cogs(self) -> None:
        """Загрузка всех когов из папки cogs"""
        cogs_dir = Path(__file__).parent / "cogs"

        for cog_file in cogs_dir.glob("*.py"):
            cog_name = f"bot_core.cogs.{cog_file.stem}"
            try:
                await self.load_extension(cog_name)
                print(f"✅ Cog loaded: {cog_name}")
            except Exception as e:
                print(f"❌ Error loading {cog_name}: {e}")

    async def start(self, *args, **kwargs) -> None:
        await self.db.connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.db.close()
        await super().close()

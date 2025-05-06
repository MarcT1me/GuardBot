from functools import wraps
from pathlib import Path

import discord
from discord.ext import commands
from discord.ext.commands import Context, errors
from discord.ext.commands._types import BotT

from loguru import logger

import bot_core.cogs
from .database import Database


class PermissionCheckError(Exception):
    def __init__(self, target: str, missing: list[str]):
        self.target = target
        self.missing = missing
        super().__init__(f"Missing permissions: {', '.join(missing)}")


class GuardBot(commands.Bot):
    def __init__(self, database: Database,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = database

    @staticmethod
    def has_permission(**permissions):
        def decorator(func):

            @wraps(func)
            async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
                # Проверка прав пользователя
                missing_user = [perm for perm in permissions if
                                not getattr(interaction.user.guild_permissions, perm, False)]
                if missing_user:
                    raise PermissionCheckError("user", missing_user)

                # Проверка прав бота
                missing_bot = [perm for perm in permissions if
                               not getattr(interaction.guild.me.guild_permissions, perm, False)]
                if missing_bot:
                    raise PermissionCheckError("bot", missing_bot)

                func(self, interaction, *args, **kwargs)

            return wrapper

        return decorator

    async def on_command_error(self, context: Context[BotT], exception: errors.CommandError, /) -> None:
        if isinstance(exception, discord.app_commands.MissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in exception.missing_permissions]
            await interaction.response.send_message(  # type: ignore
                f"❌ Вам не хватает прав: {', '.join(missing)}",
                ephemeral=True
            )
        elif isinstance(exception, discord.app_commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in exception.missing_permissions]
            await interaction.response.send_message(  # type: ignore
                f"❌ Боту не хватает прав: {', '.join(missing)}",
                ephemeral=True
            )
            if isinstance(exception, discord.Forbidden):
                await interaction.response.send_message(  # type: ignore
                    f"❌ Ошибка доступа: {exception.text}",
                    ephemeral=True
                )
        elif isinstance(exception, discord.HTTPException):
            error_msg = {
                400: "Некорректные параметры канала",
                403: "Нет прав для создания канала",
                500: "Внутренняя ошибка сервера Discord"
            }.get(exception.status, f"Ошибка API: {exception.text}")

            await interaction.response.send_message(  # type: ignore
                f"❌ Ошибка запроса: {error_msg}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(  # type: ignore
                f"❌ Неизвестная ошибка: {str(exception)}",
                ephemeral=True
            )

    @property
    def script_eng(self) -> 'bot_core.cogs.script_engine.ScriptEngine':
        return self.cogs.get("ScriptEngine")

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
                logger.success(f"✅ Cog loaded: {cog_name}\n")
            except Exception as e:
                logger.error(f"❌ Error loading {cog_name}: {e}\n")

    async def start(self, *args, **kwargs) -> None:
        await self.db.connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.db.close()
        await super().close()

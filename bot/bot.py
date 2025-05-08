from functools import wraps
from pathlib import Path

import discord
from discord.ext import commands

from loguru import logger

import bot.cogs.script_engine
from .database import GuardDatabase


class PermissionCheckError(Exception):
    def __init__(self, target: str, missing: list[str]):
        self.target = target
        self.missing = missing
        super().__init__(f"Missing permissions: {', '.join(missing)}")


class GuardBot(commands.Bot):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, database: GuardDatabase):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="/",
            intents=intents
        )
        self.db = database

    @staticmethod
    def normalize_response(response: str, reason: str) -> str:
        return response + "\nПричина: " + reason if reason else ""

    @staticmethod
    def error_handler(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            try:
                return await func(self, interaction, *args, **kwargs)

            except PermissionCheckError as e:
                missing = [perm.replace('_', ' ').title() for perm in e.missing]
                target = "боту" if e.target == "bot" else "вам"
                await interaction.response.send_message(  # type: ignore
                    f"❌ {target.capitalize()} не хватает прав: {', '.join(missing)}",
                    ephemeral=True
                )
            except discord.app_commands.MissingPermissions as e:
                missing = [perm.replace('_', ' ').title() for perm in e.missing_permissions]
                await interaction.response.send_message(  # type: ignore
                    f"❌` Вам не хватает прав. ||{', '.join(missing)}||",
                    ephemeral=True
                )
            except discord.app_commands.BotMissingPermissions as e:
                missing = [perm.replace('_', ' ').title() for perm in e.missing_permissions]
                await interaction.response.send_message(  # type: ignore
                    f"❌` Боту не хватает прав. ||{', '.join(missing)}||",
                    ephemeral=True
                )
            except discord.Forbidden as e:
                await interaction.response.send_message(  # type: ignore
                    f"❌ Ошибка доступа. ||{e.text}||",
                    ephemeral=True
                )
            except discord.HTTPException as e:
                error_msg = {
                    400: "Некорректные параметры",
                    404: "Сущность не найдена",
                    429: "Слишком много запросов",
                    500: "Внутренняя ошибка сервера Discord"
                }.get(e.status, f"Ошибка API {e.text}")

                await interaction.response.send_message(  # type: ignore
                    f"❌ Ошибка запроса. ||{error_msg}||",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(  # type: ignore
                    f"❌ Неизвестная ошибка: {str(e)}",
                    ephemeral=True
                )

        return wrapper

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

                await func(self, interaction, *args, **kwargs)

            return wrapper

        return decorator

    @property
    def script_eng(self) -> bot.cogs.script_engine.ScriptEngine:
        return self.cogs.get("ScriptEngine")

    async def setup_hook(self) -> None:
        """Асинхронная загрузка когов при запуске"""
        await self.db.connect()
        await self._load_cogs()
        await self.tree.sync()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.success(f"✅ Бот {self.user} готов к работе!")

    async def _load_cogs(self) -> None:
        """Загрузка всех когов из папки cogs"""
        cogs_dir = Path(__file__).parent / "cogs"

        for cog_file in cogs_dir.glob("*.py"):
            cog_name = f"bot.cogs.{cog_file.stem}"
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

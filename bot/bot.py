import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

from loguru import logger

import bot.cogs
from .database import GuardDatabase


class PermissionCheckError(Exception):
    def __init__(self, target: str, missing: list[str]):
        self.target = target
        self.missing = missing
        super().__init__(f"Missing permissions: {', '.join(missing)}")


class GuardBot(commands.Bot):
    instance: 'GuardBot' = None
    is_restart: bool = False

    _bot_dev_users = [
        805395077496832011,  # Marc
        1226073097136771135,  # Snaik
        278772518758776833,  # Alex
        864811730337267734,  # Just
        764118831526314004,  # Emil
    ]

    def __new__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, database: GuardDatabase):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="/",
            intents=intents
        )
        self.db = database

        self._cog_loading_event = asyncio.Event()
        self._condition = asyncio.Condition()
        self._max_completed_index = -1
        self._cog_ready_counter = 0

    @staticmethod
    def normalize_response_reason(response: str, reason: str) -> str:
        return response + "\nПричина: " + reason if reason else ""

    @staticmethod
    def normalize_response_size(response: str, size=2000, end="\n...") -> str:
        if len(response) >= size:
            return response[:size - len(end) - 1] + end
        return response

    @staticmethod
    def normalized_reason(user: discord.User, reason: str | None) -> str:
        return f"{user.name}: {reason if reason else 'unspecified'}"

    @staticmethod
    def error_handler(is_defer: bool = False):
        def decorator(func):
            @wraps(func)
            async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
                response = interaction.followup.send if is_defer else interaction.response.send_message  # type: ignore

                try:
                    return await func(self, interaction, *args, **kwargs)

                except PermissionCheckError as e:
                    missing = [perm.replace('_', ' ').title() for perm in e.missing]
                    target = "боту" if e.target == "bot" else "вам"
                    await response(
                        f"❌ {target.capitalize()} не хватает прав: {', '.join(missing)}",
                        ephemeral=True
                    )
                    logger.exception(f"{e}")
                except discord.app_commands.MissingPermissions as e:
                    missing = [perm.replace('_', ' ').title() for perm in e.missing_permissions]
                    await response(  # type: ignore
                        f"❌` Вам не хватает прав. ||{', '.join(missing)}||",
                        ephemeral=True
                    )
                    logger.exception(f"{e}")
                except discord.app_commands.BotMissingPermissions as e:
                    missing = [perm.replace('_', ' ').title() for perm in e.missing_permissions]
                    await response(  # type: ignore
                        f"❌` Боту не хватает прав. ||{', '.join(missing)}||",
                        ephemeral=True
                    )
                    logger.exception(f"{e}")
                except discord.Forbidden as e:
                    await response(  # type: ignore
                        f"❌ Ошибка доступа. ||{e.text}||",
                        ephemeral=True
                    )
                    logger.exception(f"{e}")
                except discord.HTTPException as e:
                    error_msg = {
                        400: "Некорректные параметры",
                        404: "Сущность не найдена",
                        429: "Слишком много запросов",
                        500: "Внутренняя ошибка сервера Discord"
                    }.get(e.status, f"Ошибка API {e.text}")

                    await response(  # type: ignore
                        f"❌ Ошибка запроса. ||{error_msg}||",
                        ephemeral=True
                    )
                    logger.exception(f"{e}")
                except Exception as e:
                    await response(  # type: ignore
                        f"❌ Неизвестная ошибка: {str(e)}",
                        ephemeral=True
                    )
                    logger.exception(f"{e}")

            return wrapper

        return decorator

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

    @staticmethod
    def cog_names():
        cogs_dir = Path(__file__).parent / "cogs"

        for cog_file in cogs_dir.glob("*.py"):
            yield f"bot.cogs.{cog_file.stem}"

    async def check_botdev(self, interaction: discord.Interaction) -> bool:
        # Используем await и новый метод из GuardDatabase
        if interaction.user.id in self._bot_dev_users: return True
        return False

    @property
    def script_eng(self) -> 'bot.ScriptEngine':
        cog: bot.cogs.script.ScriptCog = self.cogs.get("ScriptCog")
        return cog.engine

    @property
    def voice_state_manager(self) -> 'bot.voice_core.VoiceStateManager':
        cog: bot.cogs.voice.VoiceCog = self.cogs.get("VoiceCog")
        return cog.voice_state_manager

    async def setup_hook(self) -> None:
        """Асинхронная загрузка когов при запуске"""
        await self.load_cogs()
        await self.tree.sync()

    @commands.Cog.listener()
    async def on_ready(self):
        self._cog_loading_event.set()
        logger.success(f"✅ Бот {self.user} загрузил все данные и готов к работе!")

    async def load_cogs(self, cog_names: Optional[list[str]] = None) -> None:
        """Загрузка всех когов из папки cogs"""

        for cog_name in self.cog_names():
            if cog_names and cog_name not in cog_names:
                continue
            try:
                await self.load_extension(cog_name)
                logger.success(f"✅ Cog loaded: {cog_name}\n")
            except Exception as e:
                logger.error(f"❌ Error loading {cog_name}: {e}\n")

    async def load_extension(self, name: str, *args, **kwargs) -> None:
        try:
            await super().load_extension(name, *args, **kwargs)
            await self.on_cog_loaded()
        except Exception as e:
            logger.exception(f"Failed to load {name}: {e}")

    async def on_cog_loaded(self):
        async with self._condition:
            self._cog_ready_counter += 1

    @asynccontextmanager
    async def wait_for_cog_loading(self, index: int):
        await self._cog_loading_event.wait()
        async with self._condition:
            await self._condition.wait_for(lambda: self._max_completed_index >= index - 1)
            try:
                yield
            finally:
                if index > self._max_completed_index:
                    self._max_completed_index = index
                self._condition.notify_all()

    async def unload_cogs(self, cog_names: list[str] | None = None):
        if cog_names is None or "VoiceCog" in cog_names:
            await self.voice_state_manager.disconnect_all()

        for cog_name in self.cog_names() if not cog_names else cog_names:
            try:
                if cog_name in self.extensions:
                    await self.unload_extension(cog_name)
                    logger.success(f"♻️ Cog unloaded: {cog_name}")
            except Exception as e:
                logger.exception(f"🔥 Failed to unload {cog_name}: {e}")
                continue

    async def reload_cogs(self, cog_names: list[str] | None = None):
        await self.unload_cogs(cog_names)
        await self.load_cogs(cog_names)

        names = self.cog_names() if not cog_names else cog_names

        for cog_name in names:
            cog = self.get_cog(cog_name)
            if (
                    cog
                    and hasattr(cog, "on_ready")
                    and hasattr(cog, "_is_ready") and not getattr(cog, "_is_ready")
            ):
                await cog.on_ready()

        if cog_names is None or "ScriptEngine" in cog_names:
            await self.script_eng.load_scripts()

    async def start(self, *args, **kwargs) -> None:
        await self.db.connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.voice_state_manager.disconnect_all()
        await self.db.close()
        await super().close()

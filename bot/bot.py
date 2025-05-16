from functools import wraps
from pathlib import Path

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

    bot_dev_users = [805395077496832011, 1226073097136771135]

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
        if interaction.user.id in self.bot_dev_users: return True
        return False

    @property
    def script_eng(self) -> 'bot.cogs.script_engine.ScriptEngine':
        return self.cogs.get("ScriptEngine")

    @property
    def event_cog(self) -> 'bot.cogs.events.EventCog':
        return self.cogs.get("EventCog")

    @property
    def voice_cog(self) -> 'bot.cogs.voice.VoiceCog':
        return self.cogs.get("VoiceCog")

    async def setup_hook(self) -> None:
        """Асинхронная загрузка когов при запуске"""
        await self.db.connect()
        await self._load_cogs()
        await self.tree.sync()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.success(f"✅ Бот {self.user} загрузил все данные и готов к работе!")
        await self.tree.sync()

    async def _load_cogs(self) -> None:
        """Загрузка всех когов из папки cogs"""

        for cog_name in self.cog_names():
            try:
                await self.load_extension(cog_name)
                logger.success(f"✅ Cog loaded: {cog_name}\n")
            except Exception as e:
                logger.error(f"❌ Error loading {cog_name}: {e}\n")

    async def re_load_cogs(self, cog_names: list[str] | None = None):
        """Перезагружает коги (все или указанные) без перезапуска бота"""

        if cog_names is None or "VoiceCog" in cog_names:
            await self.voice_cog.disconnect_all()

        for cog_name in self.cog_names() if not cog_names else cog_names:
            try:
                if cog_name in self.extensions:
                    await self.unload_extension(cog_name)  # Выгружаем старую версию
                    await self.load_extension(cog_name)  # Загружаем обновленную
                    logger.success(f"♻️ Cog reloaded: {cog_name}")
                else:
                    await self.load_extension(cog_name)
                    logger.success(f"✅ New cog loaded: {cog_name}")
            except Exception as e:
                logger.error(f"🔥 Failed to reload {cog_name}: {e}")
                continue

        if cog_names is None or "ScriptEngine" in cog_names:
            await self.script_eng.on_ready()

        # Синхронизация команд с серверами Discord
        await self.tree.sync()

    async def start(self, *args, **kwargs) -> None:
        await self.db.connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.voice_cog.disconnect_all()
        await self.db.close()
        await super().close()

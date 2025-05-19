from typing import Any, Type, Callable, Optional, Iterable, Iterator
from abc import ABC, abstractmethod
from pathlib import Path
from enum import Enum, auto

import asyncio
import datetime
import random
import discord
import math

from discord.ext import commands

from RestrictedPython import safe_builtins
import ast

from loguru import logger

from bot.bot import GuardBot, GuardDatabase


class _SafeDiscordApi:
    Interaction = discord.Interaction
    Message = discord.Message
    Member = discord.Member
    Guild = discord.Guild
    Role = discord.Role

    TextChannel = discord.TextChannel
    VoiceChannel = discord.VoiceChannel
    StageChannel = discord.StageChannel
    VoiceState = discord.VoiceState

    Colour = discord.Colour
    Asset = discord.Asset

    AllowedMentions = discord.AllowedMentions
    File = discord.File
    Embed = discord.Embed


class _SafeDataBase:
    user: GuardDatabase.user = None
    script: GuardDatabase.script = None
    role: GuardDatabase.role = None
    channel: GuardDatabase.channel = None
    template: GuardDatabase.template = None

    def __init__(self, server: GuardDatabase.server):
        self.__server = server

    async def init(self, _id: int, **kwargs):
        self.__server = await GuardDatabase.save_server(
            guild_id=_id,
            **kwargs
        )

    def server_addition(self, name: str) -> Any:
        return self.__server.additions.get(name)

    async def save_server_addition(self, name: str, value: Any):
        self.__server.additions[name] = value
        await self.__server.save()

    async def get_user(self, *, user_id: int) -> GuardDatabase.user | None:
        return await GuardDatabase.get_user(server=self.__server, user_id=user_id)

    async def save_user(self, *, user_id: int,
                        **additions) -> GuardDatabase.user:
        return await GuardDatabase.save_user(guild_id=self.__server.guild_id, user_id=user_id, **additions)

    async def remove_user(self, *, user_id: int) -> None:
        await GuardDatabase.remove_user(server=self.__server, user_id=user_id)

    async def get_channels(self, *, channel_type) -> list[GuardDatabase.channel]:
        return await GuardDatabase.get_channels(server=self.__server, channel_type=channel_type)

    async def get_channel_by_id(self, *, channel_id) -> GuardDatabase.channel | None:
        db_channel = await GuardDatabase.get_channel_by_id(channel_id=channel_id)
        if db_channel:
            channel_guild_id = (await db_channel.server.values("guild_id"))["guild_id"]
            return db_channel if channel_guild_id == self.__server.guild_id else None

    async def save_factory_channel(self, *, channel_id: int,
                                   cooldown: float = 0.0, is_active=False) -> GuardDatabase.channel:
        return await GuardDatabase.save_factory_channel(
            server_id=self.__server.guild_id,
            channel_id=channel_id,

            cooldown=cooldown,
            is_active=is_active
        )

    async def save_temp_channel(self, *, channel_id: int,
                                parent_channel_id: int, owner_id) -> GuardDatabase.channel:
        return await GuardDatabase.save_temp_channel(
            server_id=self.__server.guild_id,
            channel_id=channel_id,

            parent_channel_id=parent_channel_id,
            owner_id=owner_id,
        )

    async def save_channel(self, *, channel_id: int, channel_type: str,
                           **additions) -> GuardDatabase.channel:
        return await GuardDatabase.save_channel(
            server_id=self.__server.guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
            **additions
        )

    async def delete_channel(self, *, channel_id: int) -> None:
        db_channel = await GuardDatabase.get_channel_by_id(channel_id=channel_id)
        if db_channel:
            channel_guild_id = (await db_channel.server.values("guild_id"))["guild_id"]
            if channel_guild_id == self.__server.guild_id:
                await GuardDatabase.delete_channel(channel_id=channel_id)

    async def get_template(self, *, template_name: str) -> GuardDatabase.template | None:
        return await GuardDatabase.get_template(server=self.__server, template_name=template_name)

    async def get_template_by_id(self, *, template_id: int) -> GuardDatabase.template | None:
        db_template = await GuardDatabase.get_template_by_id(template_id=template_id)
        if db_template:
            template_guild_id = (await db_template.server.values("guild_id"))["guild_id"]
            return db_template if db_template and template_guild_id == self.__server.guild_id else None

    async def save_template(self, *, name: str, content: str, is_active: bool = False) -> GuardDatabase.template:
        return await GuardDatabase.save_template(
            server_id=self.__server.guild_id,
            name=name,
            content=content,
            is_active=is_active
        )


class _ScriptGuild:
    def __init__(self, guild_id: int, db: _SafeDataBase):
        guild = GuardBot.instance.get_guild(guild_id)
        if guild:
            self.id: int = guild.id
            self.name: str = guild.name
            self.members: list[discord.Member] = getattr(guild, "members")
        else:
            self.id: int = None
            self.name: str = None
            self.members: list[discord.Member] = []
        self.db: _SafeDataBase = db

    def set_async_event(self, name: str, event: asyncio.Event) -> None:
        ScriptEngine.async_events.setdefault(self.id, {})[name] = event

    def get_async_event(self, name: str) -> asyncio.Event:
        return ScriptEngine.async_events.setdefault(self.id, {}).get(name)


class _SafeBot:
    def __init__(self, bot_user: discord.User, script_guild: _ScriptGuild):
        self.name = bot_user.name
        self.global_name = bot_user.global_name
        self.mention: str = getattr(bot_user, "mention")
        self.color: discord.Colour = getattr(bot_user, "color")
        self.banner: discord.Asset = getattr(bot_user, "banner")
        self.avatar: discord.Asset = getattr(bot_user, "avatar")
        self.guild = script_guild

    async def setup_guild_only_cog(self, cog: commands.Cog):
        bot = GuardBot.instance
        guild = bot.get_guild(self.guild.id)
        if cog.__cog_name__ in bot.cogs:
            await bot.remove_cog(cog.__cog_name__, guild=guild)
        await bot.add_cog(cog, override=True, guild=guild)
        await bot.tree.sync(guild=guild)

    err_handler = GuardBot.error_handler
    has_permission = GuardBot.has_permission
    normalize_response_size = GuardBot.normalize_response_size
    normalized_reason = GuardBot.normalized_reason
    normalize_response_reason = GuardBot.normalize_response_reason


class BaseScript(ABC):
    """Абстрактный базовый класс для скриптов"""
    lang = None

    class _EnvModule:
        def __init__(self, env: dict[str, Any]):
            self.__dict__["__env"] = env

        def __getattr__(self, item):
            return self.__dict__["__env"].get(item)

        def __setattr__(self, key, value):
            if key in self.__dict__["__env"]:
                self.__dict__["__env"][key] = value
            super().__setattr__(key, value)

    class __ScriptEnvObj:
        def __init__(self, obj: object, /, include_all: bool = True, **filter):
            for name, value in self.__iter__names(obj, include_all, **filter):
                setattr(self, name, value)

        @staticmethod
        def __iter__names(obj: object, include_all: bool, **filter) -> Iterator[tuple[str, object]]:
            for attr in dir(obj):
                condition: bool = False
                try:
                    condition = not attr.startswith('_') and attr not in filter and hasattr(obj, attr)
                    condition = condition if include_all else not condition
                except DeprecationWarning:
                    condition = False
                finally:
                    if condition:
                        yield attr, getattr(obj, attr)

    @staticmethod
    def calculate(expr: str) -> float:
        try:
            # Ограничиваем доступ только к математическим функциям
            return eval(
                expr,
                {"__builtins__": None},  # Блокируем все встроенные функции
                {
                    "math": {attr: getattr(math, attr)
                             for attr in dir(math)
                             if not attr.startswith('_')}  # Только публичные методы
                }
            )
        except Exception as e:
            raise ValueError(f"Calculation Error: {str(e)}")

    @staticmethod
    def iterate[T](expr: Iterable[T]) -> Iterator[tuple[int, T]]:
        assert isinstance(expr, Iterable), "iterate operate only with Iterable"

        for i, value in enumerate(expr):
            yield i, value

    def include(self, script_name: str, as_name: str = None) -> Any:
        if script_name == self.name:
            raise ValueError(f"Cannot include self: {script_name}")

        include_script = self.engine.get_script(self.code_env["guild_id"], script_name)

        if not include_script:
            raise ImportError(f"Script {script_name} not found")

        as_name = as_name or script_name
        ret = BaseScript._EnvModule(include_script.code_env)
        self.code_env[as_name] = ret
        return ret

    __script_env = {
        "__builtins__": {
            "__name__": __name__,
            "classmethod": classmethod,
            "staticmethod": staticmethod,
            "property": property,
            "dir": dir,
            **safe_builtins
        },

        "discord": __ScriptEnvObj(_SafeDiscordApi),
        "Cog": commands.Cog,
        "Group": commands.Group,
        "GroupCog": commands.GroupCog,
        "app_commands": __ScriptEnvObj(
            discord.app_commands, include_all=False,
            command=True,
            describe=True
        ),
        "ui": __ScriptEnvObj(discord.ui),

        "datetime": __ScriptEnvObj(datetime),
        "asyncio": __ScriptEnvObj(asyncio),
        "random": __ScriptEnvObj(random),

        "ScriptDatabase": __ScriptEnvObj(_SafeDataBase),
        "ScriptGuild": __ScriptEnvObj(_ScriptGuild),
        "Bot": __ScriptEnvObj(_SafeBot),

        "Any": Any,
        "Callable": Callable,
        "Optional": Optional,

        "logger": logger,
        "Enum": Enum,
        "auto": auto,

        "calculate": calculate,
        "iterate": iterate
    }

    def __init__(self, engine: 'ScriptEngine', guild_id: int, code: str, name: str):
        self.engine: ScriptEngine = engine
        self.code: str = code
        self.guild_id = guild_id
        self.name = name
        self.filename = f"{guild_id}\\{name}"
        self._included_scripts: set[str] = set()

        self.compiled_code: Optional[str] = None
        self.code_env = dict()

        for name, value in {
            **BaseScript.__script_env,
            "guild_id": guild_id,
            "include": self.include
        }.items():
            self.code_env[name] = value

        self.main_func: Optional[Callable] = None

    async def execute_main_func(self, context):
        exec(self.compiled_code, self.code_env)
        await self.main_func(**(await self.create_safe_context(context)))

    def _update_main_func(self) -> Callable:
        try:
            self.main_func = self.code_env["main"]
        except AttributeError as e:
            raise AttributeError(f"Code not implement enter point: {str(e)}")
        finally:
            if not asyncio.iscoroutinefunction(self.main_func):
                raise TypeError("Main function must be async")

    async def create_safe_context(self, context: dict) -> dict:
        context["bot"] = BaseScript.__ScriptEnvObj(_SafeBot(
            self.engine.bot.user,
            BaseScript.__ScriptEnvObj(_ScriptGuild(
                self.guild_id,
                BaseScript.__ScriptEnvObj(_SafeDataBase(
                    await GuardDatabase.get_server(guild_id=self.guild_id)
                ))
            ))
        ))

        if msg := context.get("msg"):
            context["msg"] = BaseScript.__ScriptEnvObj(msg, interaction=False)
        if member := context.get("member"):
            context["member"] = BaseScript.__ScriptEnvObj(member, interaction=False)
        if guild := context.get("guild"):
            context["guild"] = BaseScript.__ScriptEnvObj(guild, interaction=False)

        return context

    @abstractmethod
    def compile(self) -> 'BaseScript':
        pass

    @abstractmethod
    async def execute(self, guild_id: int, context: dict) -> Any:
        self.code_env["guild_id"] = guild_id


class PythonScript(BaseScript):
    """Обработчик Python-скриптов"""
    lang = "py"

    def compile(self) -> 'PythonScript':
        self.normalize()
        super().compile()

        self._validate_syntax()
        exec(
            compile(self.compiled_code, self.filename, "exec"),
            self.code_env
        )

        if "LIB" not in self.name:
            self._update_main_func()
        return self

    def normalize(self) -> None:
        context = self.code.replace("from bot.script_evs import *", "")
        context = context.replace("GuardBot", "Any")

        new_content = ""
        for line in context.split("\n"):
            if "import" in line:
                if "__import__" in line:
                    raise ImportError(f"Not allow builtins: __import__")

                data = line.split()

                if not self.engine.scripts.get(self.guild_id, {}).get(data[1]):
                    raise ImportError(f"Not allow import: {data[1]}.\nCan import only scripts")

                l = len(data)
                if l == 2:
                    line = f"include(\"{data[1]}\")"
                elif l == 4:
                    line = f"include(\"{data[1]}\", \"{data[3]}\")"

            new_content += line + "\n"

        self.compiled_code = new_content

    def _validate_syntax(self) -> None:
        """AST-валидация с разрешением асинхронных конструкций"""
        forbidden_nodes = (
            ast.ImportFrom,
            ast.Import,
            ast.Lambda,
            ast.With,
            # Добавляем исключения для async/await
        )

        for node in ast.walk(ast.parse(self.compiled_code)):
            if isinstance(node, forbidden_nodes):
                if isinstance(node, ast.Call):
                    func_name = getattr(node.func, 'id', '')
                    if func_name in ('eval', 'exec', 'open'):
                        raise SyntaxError(f"Dangerous function: {func_name}")
                else:
                    raise SyntaxError(f"Forbidden: {type(node).__name__}")

            # Разрешаем async def и await
            if isinstance(node, ast.AsyncFunctionDef):
                pass  # Явно разрешаем
            if isinstance(node, ast.Await):
                pass  # Явно разрешаем

    async def execute(self, guild_id: int, context: dict) -> Any:
        await super().execute(guild_id, context)
        try:
            await asyncio.wait_for(
                self.execute_main_func(context),
                timeout=self.engine.script_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Script {self.filename} timeout: {self.engine.script_timeout}s")
            raise


class ScriptEngine(commands.Cog):
    """Ядро системы управления скриптами"""
    async_events: dict[int, dict[str, asyncio.Event]] = {}

    def __init__(
            self, bot, /,
            scripts_dir="scripts",
            script_timeout: int = 30
    ):
        self.bot: GuardBot = bot
        self.scripts_dir = scripts_dir

        self.scripts: dict[int | None, dict[str, BaseScript]] = {
            None: {}
        }

        self.script_timeout = script_timeout

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async with self.bot.wait_for_cog_loading(0):
            logger.debug("Loading scripts")

            self.scripts[None].update(
                self._compile_script(
                    None,
                    PythonScript,
                    "EMPTY",
                    "async def main(**kwargs): ..."
                )
            )

            await self.load_scripts_from_dir()
            await self.load_scripts_from_db()
            await self.guilds_on_ready()

    async def _get_server_scripts(self, guild_id: int) -> dict:
        if guild_id not in self.scripts:
            server, _ = await self.bot.db.get_server(guild_id=guild_id)
            self.scripts[guild_id] = {
                script.name: script
                for script in await server.scripts.filter(is_active=True)
            }

    async def guilds_on_ready(self):
        logger.info("setup on_ready.data for guilds\n")

        for guild in self.bot.guilds:
            script_name, guild_id = await self.bot.event_cog.get_event_script_name(None, "on_ready")
            await self.bot.script_eng.execute(
                script_name,
                None,
                script_guild_id=guild.id,
                guild=guild
            )
            logger.success(f"`{guild}` data ready\n")

    async def load_scripts_from_db(self) -> list:
        scripts = await GuardDatabase.script.filter(is_active=True)
        load_errors = []

        # create slots  (for imports)
        for script in scripts:
            if not self.scripts[script.server.guild_id]:
                self.scripts[script.server.guild_id] = {}
            self.scripts[script.server.guild_id].update({
                script.name: self.scripts[None]["EMPTY"]
            })

        for script in scripts:
            try:
                self.scripts[script.server.guild_id].update(
                    self._compile_script(
                        script.server.guild_id,
                        PythonScript,
                        script.name,
                        script.content
                    )
                )

                logger.success(f"Script loaded: {script.name}")

            except Exception as e:
                logger.error(f"Failed to fetch {script.name}: {e}")
                load_errors.append(
                    (e, f"Failed to fetch {script.name}: {e}")
                )
        return load_errors

    async def load_scripts_from_dir(self) -> None:
        """Рекурсивная загрузка скриптов из директории"""
        load_errors = []

        # create slots  (for imports)
        for script_path in Path(self.scripts_dir).glob("**/*"):
            if script_path.is_file() and script_path.suffix in ('.lua', '.py'):
                self.scripts[None].update({
                    script_path.stem: self.scripts[None]["EMPTY"]
                })

        for script_path in Path(self.scripts_dir).glob("**/*"):
            if script_path.is_file() and script_path.suffix in ('.lua', '.py'):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    self.scripts[None].update(
                        **self._compile_script(
                            None,
                            PythonScript,
                            script_path.stem,
                            content
                        )
                    )

                    logger.success(f"Script loaded: {script_path.stem}")
                except Exception as e:
                    logger.exception(f"Failed to load {script_path.name}: {e}")
                    load_errors.append(
                        (e, f"Failed to load {script_path.name}: {e}")
                    )
        return load_errors

    def _compile_script(
            self,
            guild_id: int,
            script_type: Type[BaseScript],
            name: str,
            content: str
    ) -> dict:
        """Компиляция отдельного скрипта"""
        return {name: script_type(self, guild_id, content, name).compile()}

    def get_script(self, guild_id: int, name: str) -> BaseScript:
        script_field = self.scripts.get(guild_id)
        if not script_field: return None

        script = script_field.get(name)
        if not script: script = self.scripts[None].get(name)
        return script

    async def execute(self, name: str, guild_id: int | None, script_guild_id: int | None = None, **context) -> Any:
        """Запуск скрипта по имени"""
        if script := self.get_script(guild_id, name):
            try:
                if script_guild_id:
                    guild_id = script_guild_id
                return await script.execute(guild_id, context)
            except Exception as e:
                logger.exception(f"Error in script {script.filename}: {e}")
                raise
        logger.error(f"Script {name} not found")
        return None


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptEngine loading")
    await bot.add_cog(
        ScriptEngine(
            bot,
            script_timeout=600
        )
    )

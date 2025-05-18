from typing import Any, Type, Callable, Optional, Iterable, Iterator
from copy import copy
from abc import ABC, abstractmethod
from pathlib import Path

import asyncio
import datetime
import random
import discord
import math

from discord.ext import commands

import lupa
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
        return db_channel if db_channel and db_channel.server.guild_id == self.__server.guild_id else None

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
        if db_channel and db_channel.server.guild_id == self.__server.guild_id:
            await GuardDatabase.delete_channel(channel_id=channel_id)

    async def get_template(self, *, template_name: str) -> GuardDatabase.template | None:
        return await GuardDatabase.get_template(server=self.__server, template_name=template_name)

    async def get_template_by_id(self, *, template_id: int) -> GuardDatabase.template | None:
        db_template = await GuardDatabase.get_template_by_id(template_id=template_id)
        return db_template if db_template and db_template.server.guild_id == self.__server.guild_id else None

    async def save_template(self, name: str, content: str, is_active: bool = False) -> GuardDatabase.template:
        return await GuardDatabase.save_template(
            server_id=self.__server.guild_id,
            name=name,
            content=content,
            is_active=is_active
        )


class _ScriptGuild:
    def __init__(self, guild: discord.Guild, db: _SafeDataBase):
        self.guild: discord.Guild = guild
        self.db = db

    def set_async_event(self, name: str, event: asyncio.Event) -> None:
        ScriptEngine.async_events.setdefault(self.guild.id, {})[name] = event

    def get_async_event(self, name: str) -> asyncio.Event:
        return ScriptEngine.async_events.setdefault(self.guild.id, {}).get(name)


class _SafeBot:
    def __init__(self, bot_user: discord.User, script_guild: _ScriptGuild):
        self.name = bot_user.name
        self.global_name = bot_user.global_name
        self.mention: str = getattr(bot_user, "mention")
        self.color: discord.Colour = getattr(bot_user.color, "color")
        self.banner: discord.Asset = getattr(bot_user, "banner")
        self.avatar: discord.Asset = getattr(bot_user, "avatar")
        self.guild = script_guild

    err_handler = GuardBot.error_handler
    has_permission = GuardBot.has_permission
    normalize_response_size = GuardBot.normalize_response_size
    normalized_reason = GuardBot.normalized_reason
    normalize_response_reason = GuardBot.normalize_response_reason


class BaseScript(ABC):
    """Абстрактный базовый класс для скриптов"""
    lang = None

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
        for i, value in enumerate(expr):
            yield i, value

    def include(self, script_name: str, as_name: str = None) -> None:
        include_script = self.engine.get_script(self["guild_id"], self.code_env)
        if as_name is None: as_name = script_name
        self[as_name] = include_script

    def set_async_event(self, name: str, event: asyncio.Event) -> None:
        self.engine.async_events.setdefault(self["guild_id"], {})[name] = event

    def get_async_event(self, name: str) -> asyncio.Event:
        return self.engine.async_events.setdefault(self["guild_id"], {}).get(name)

    __script_env = {
        "__builtins__": safe_builtins,

        "discord": __ScriptEnvObj(_SafeDiscordApi),
        "Cog": commands.Cog,
        "Group": commands.Group,
        "app_commands": __ScriptEnvObj(
            discord.app_commands, include_all=False,
            command=True,
            describe=True
        ),
        "ui": __ScriptEnvObj(discord.ui),

        "datetime": __ScriptEnvObj(datetime),
        "asyncio": __ScriptEnvObj(asyncio),
        "random": __ScriptEnvObj(random),

        "Any": Any,
        "Callable": Callable,
        "Optional": Optional,
        "logger": logger,

        "err_handler": GuardBot.error_handler,
        "has_permission": GuardBot.has_permission,
        "normalize_response_size": GuardBot.normalize_response_size,
        "normalized_reason": GuardBot.normalized_reason,
        "normalize_response_reason": GuardBot.normalize_response_reason,

        "calculate": calculate,
        "iterate": iterate
    }
    __script_env.get("__builtins__", {}).update(**safe_builtins)
    __script_env.get("__builtins__", {})["__name__"] = __name__

    def __init__(self, engine: 'ScriptEngine'):
        self.engine: ScriptEngine = engine

        self.code_env: dict | object = None
        self.code: Optional[str] = None
        self.filename: Optional[str] = None
        if self.lang == "py":
            self.code_env = dict()
        elif self.lang == "lua":
            self.code_env = self.engine.lua_runtime.table()

        for name, value in {
            **BaseScript.__script_env,

            "guild_id": None,
            "include": self.include,
            "set_async_event": self.set_async_event,
            "get_async_event": self.get_async_event,
        }.items(): self[name] = value

        self.main_func: Callable = None

    def __getitem__(self, item: str) -> Any:
        try:
            if isinstance(self.code_env, dict):
                return self.code_env[item]
            return getattr(self.code_env, item)
        except Exception as e:
            raise AttributeError(f"Cant find item in script env: {str(e)}")

    def __setitem__(self, item: str, value: Any) -> None:
        try:
            if isinstance(self.code_env, dict):
                self.code_env[item] = value
                return
            setattr(self.code_env, item, value)
        except Exception as e:
            raise AttributeError(f"Cant find item in script env: {str(e)}")

    def _update_main_func(self) -> Callable:
        try:
            self.main_func = self["main"]
        except AttributeError as e:
            raise AttributeError(f"Code not implement enter point: {str(e)}")
        finally:
            if not asyncio.iscoroutinefunction(self.main_func):
                raise TypeError("Main function must be async")

    def create_safe_context(self, context: dict) -> dict:
        context["bot"] = BaseScript.__ScriptEnvObj(self.engine.bot)

        if msg := context.get("msg"):
            context["msg"] = BaseScript.__ScriptEnvObj(msg, interaction=False)
        if member := context.get("member"):
            context["member"] = BaseScript.__ScriptEnvObj(member, interaction=False)
        if guild := context.get("guild"):
            context["guild"] = BaseScript.__ScriptEnvObj(guild, interaction=False)
        if interaction := context.get("interaction"):
            context["interaction"] = BaseScript.__ScriptEnvObj(interaction)

        return context

    @abstractmethod
    def compile(self, guild_id: int, content: str, name: str) -> 'BaseScript':
        self.code = content
        self.filename = f"{guild_id}\\{name}"

    @abstractmethod
    async def execute(self, guild_id: int, context: dict) -> Any:
        self["guild_id"] = guild_id


class LuaScript(BaseScript):
    """Обработчик Lua-скриптов"""
    lang = "lua"

    def compile(self, guild_id: int, content: str, name: str) -> 'LuaScript':
        super().compile(guild_id, content, name)
        loader = self.engine.lua_runtime.eval('''
            function(env, code)
                local chunk, err = load(code, nil, 't', env)
                if not chunk then return nil, err end
                return chunk()
            end
        ''')

        success, result = loader(self.code_env, content)
        if not success:
            raise RuntimeError(f"Lua error in script {self.filename}: {result}")

        self._update_main_func()
        return self

    async def execute(self, guild_id: int, context: dict) -> Any:
        await super().execute(guild_id, context)
        return await asyncio.to_thread(
            self.main_func,
            **self.create_safe_context(context)
        )


class PythonScript(BaseScript):
    """Обработчик Python-скриптов"""
    lang = "py"

    def compile(self, guild_id: int, content: str, name: str) -> 'PythonScript':
        code = self.normalize(guild_id, content)
        self._validate_syntax(code)
        super().compile(guild_id, code, name)
        exec(
            compile(code, self.filename, "exec"),
            self.code_env
        )
        self._update_main_func()
        return self

    def normalize(self, guild_id: int, context: str) -> str:
        context = context.replace("from bot.script_evs import *", "")
        context = context.replace("GuardBot", "Any")

        new_content = ""
        for line in context.split("\n"):
            if "import" in line:
                if "__import__" in line:
                    raise ImportError(f"Not allow builtins: __import__")

                data = line.split()

                if not self.engine.scripts.get(guild_id, {}).get(data[1]):
                    raise ImportError(f"Not allow import: {data[1]}.\nCan import only scripts")

                l = len(data)
                if l == 2:
                    line = f"include(\"{data[1]}\")\n"
                elif l == 4:
                    line = f"include(\"{data[1]}\", \"{data[3]}\")\n"

            new_content += line + "\n"

        return new_content

    @staticmethod
    def _validate_syntax(code: str) -> None:
        """AST-валидация с разрешением асинхронных конструкций"""
        forbidden_nodes = (
            ast.ImportFrom,
            ast.Import,
            ast.Lambda,
            ast.With,
            # Добавляем исключения для async/await
        )

        for node in ast.walk(ast.parse(code)):
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
                self.main_func(**self.create_safe_context(context)),
                timeout=self.engine.script_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Script {self.filename} timeout: {self.engine.script_timeout}s")
            raise


class ScriptEngine(commands.Cog):
    """Ядро системы управления скриптами"""
    async_events: dict[int, dict[str, asyncio.Event]] = {}

    def __init__(
            self, bot, lua_runtime: lupa.LuaRuntime, /,
            scripts_dir="scripts",
            script_timeout: int = 30
    ):
        self.bot: GuardBot = bot
        self.scripts_dir = scripts_dir
        self.lua_runtime = lua_runtime

        self.scripts: dict[int | None, dict[str, BaseScript]] = {
            None: {}
        }

        self.script_timeout = script_timeout

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async with self.bot.wait_for_cog_loading(0):
            logger.debug("Loading scripts")
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
        for script in scripts:
            try:
                if script.server.guild_id not in self.scripts:
                    self.scripts[script.server.guild_id] = {}

                self.scripts[script.server.guild_id].update(
                    self._compile_script(
                        script.server.guild_id,
                        LuaScript if script.type == 'lua' else PythonScript,
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
        for script_path in Path(self.scripts_dir).glob("**/*"):
            if script_path.is_file() and script_path.suffix in ('.lua', '.py'):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    self.scripts[None].update(
                        self._compile_script(
                            None,
                            LuaScript if script_path.suffix == '.lua' else PythonScript,
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
        return {name: script_type(self).compile(guild_id, content, name)}

    async def get_script(self, guild_id: int, name: str) -> BaseScript:
        script_field = self.scripts.get(guild_id)
        if not script_field: return None

        script = script_field.get(name)
        if not script: script = self.scripts[None].get(name)
        return script

    async def execute(self, name: str, guild_id: int | None, script_guild_id: int | None = None, **context) -> Any:
        """Запуск скрипта по имени"""
        if script := await self.get_script(guild_id, name):
            try:
                if script_guild_id: guild_id = script_guild_id
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
            lupa.LuaRuntime(),
            script_timeout=600
        )
    )


if __name__ == "__main__":
    eng = ScriptEngine(None, lupa.LuaRuntime())
    eng.scripts[None] = {"Some2": object()}
    scr = PythonScript(eng).compile(None, """

class Some():
    prop: int = 0
    
async def main(*, bot: GuardBot, member: discord.Member):
    channel = await bot.fetch_channel(123)
    await channel.send(f"Hello {member.mention}!")
    await asyncio.sleep(1)
    return "Done"
""", "test")
    print(scr.code)

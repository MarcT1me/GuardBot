from typing import Any, Type, Callable, Optional
from abc import ABC, abstractmethod
from pathlib import Path

import asyncio
import datetime
import random
import discord
import math

from discord.ext import commands

import lupa
from loguru import logger

from bot.bot import GuardBot, GuardDatabase


class BaseScript(ABC):
    """Абстрактный базовый класс для скриптов"""
    lang = None

    class __ScriptEnvObj:
        def __init__(self, obj: object, excepts: tuple[str] = ()):
            for name, value in {
                attr: getattr(obj, attr)
                for attr in dir(obj)
                if not attr.startswith('_') and attr not in excepts
            }.items(): setattr(self, name, value)

    __script_env = {
        "discord": __ScriptEnvObj(discord, excepts=("ext",)),
        "Cog": commands.Cog,
        "app_commands": __ScriptEnvObj(discord.app_commands),

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
    }

    def __init__(self, engine: 'ScriptEngine'):
        self.engine: ScriptEngine = engine

        self.code_env: dict | object = None
        if self.lang == "py":
            self.code_env = dict()
        elif self.lang == "lua":
            self.code_env = self.engine.lua_runtime.table()

        for name, value in {
            **BaseScript.__script_env,

            "guild_id": None,
            "include": self.include,
            "calculate": self.safe_calculate,
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

    @staticmethod
    def safe_calculate(expr: str) -> float:
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

    def include(self, script_name: str, as_name: str = None) -> None:
        include_script = self.engine.get_script(self["__guild_id__"], self.code_env)
        if as_name is None: as_name = script_name
        self[as_name] = include_script

    def create_safe_context(self, context: dict) -> dict:
        context["bot"] = self.engine.bot
        return context

    @abstractmethod
    def compile(self, content: str) -> 'BaseScript':
        pass

    @abstractmethod
    async def execute(self, guild_id: int, context: dict) -> Any:
        self["guild_id"] = guild_id


class LuaScript(BaseScript):
    """Обработчик Lua-скриптов"""
    lang = "lua"

    def compile(self, content: str) -> 'LuaScript':
        loader = self.engine.lua_runtime.eval('''
            function(env, code)
                local chunk, err = load(code, nil, 't', env)
                if not chunk then return nil, err end
                return chunk()
            end
        ''')

        success, result = loader(self.code_env, content)
        if not success:
            raise RuntimeError(f"Lua error: {result}")

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

    def compile(self, content: str) -> 'PythonScript':
        exec(
            self.normalize(content),
            self.code_env
        )

        self._update_main_func()
        return self

    iter = 0

    def normalize(self, context: str) -> str:
        context = context.replace("from bot.script_evs import *", "")
        context = context.replace("GuardBot", "Any")

        new_content = ""
        for line in context.split("\n"):
            if line.startswith("import"):
                data = line.split()

                l = len(data)
                if l != 2 or (l != 4 and "as" not in line):
                    raise ImportError(f"Not allow import in script: {line}")

                new_content += f"include(\"{data[1]}\", " + (
                    f"\"{data[3]}\"" if "as" in line else "None"
                ) + ")" + "\n"
                continue

            new_content += line + "\n"

        # with open(f"__test__\\scripts\\script{PythonScript.iter}.py", mode="w", encoding="utf-8") as f:
        #     f.write(new_content)
        #     PythonScript.iter += 1

        return new_content

    async def execute(self, guild_id: int, context: dict) -> Any:
        await super().execute(guild_id, context)
        return await self.main_func(**self.create_safe_context(context))


class ScriptEngine(commands.Cog):
    """Ядро системы управления скриптами"""

    def __init__(
            self, bot, scripts_dir="scripts", /,
            lua_runtime: lupa.LuaRuntime = lupa.LuaRuntime(),
            script_timeout: int = 30
    ):
        self.bot: GuardBot = bot
        self.scripts_dir = scripts_dir
        self.lua_runtime = lua_runtime

        self.scripts: dict[int | None, dict[str, BaseScript]] = {
            None: {}
        }

        self.script_timeout = script_timeout

    async def _get_server_scripts(self, guild_id: int) -> dict:
        if guild_id not in self.scripts:
            server, _ = await self.bot.db.get_server(guild_id)
            self.scripts[guild_id] = {
                script.name: script
                for script in await server.scripts.filter(is_active=True)
            }

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logger.debug("Loading scripts")
        await self.load_scripts_from_dir()
        await self.load_scripts_from_db()
        await self.guilds_on_ready()

    async def guilds_on_ready(self):
        logger.info("setup on_ready.data for guilds\n")

        for guild in self.bot.guilds:
            script_name, guild_id = await self.bot.event_cog.get_event_script_name(None, "on_ready")
            await self.bot.script_eng.execute(
                script_name,
                None,
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
            script_type: Type[BaseScript],
            name: str,
            content: str
    ) -> dict:
        """Компиляция отдельного скрипта"""
        script = script_type(self).compile(content)
        return {name: script}

    async def get_script(self, guild_id: int, name: str) -> BaseScript:
        script_field = self.scripts.get(guild_id)
        if not script_field: return None

        script = script_field.get(name)
        if not script: script = self.scripts[None].get(name)
        return script

    async def execute(self, name: str, guild_id: int | None, **context) -> Any:
        """Запуск скрипта по имени"""
        if script := await self.get_script(guild_id, name):
            try:
                return await script.execute(guild_id, context)
            except Exception as e:
                logger.exception(f"Script error in {name}: {e}")
                raise
        logger.error(f"Script {name} not found")
        return None


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptEngine loading")
    await bot.add_cog(ScriptEngine(bot))

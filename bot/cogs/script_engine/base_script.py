from abc import ABC, abstractmethod
import asyncio
import datetime
from enum import Enum, auto
import json
import math
import random
from typing import Any, Callable, Iterable, Iterator, Optional, Self, Type

from RestrictedPython import safe_builtins
import discord
from discord.ext import commands
from loguru import logger

import bot
from bot import GuardDatabase
from .env_types import _SafeEnvObject, _EnvObject
from .safe_types import _SafeBot, _SafeDataBase, _SafeDiscordApi, _ScriptGuild


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


def iterate[T](expr: Iterable[T]) -> Iterator[tuple[int, T]]:
    assert isinstance(expr, Iterable), "iterate operate only with Iterable"

    for i, value in enumerate(expr):
        yield i, value


_script_types = {}
_static_script_env = {
    "__builtins__": {
        **safe_builtins,

        "__name__": __name__,
        "classmethod": classmethod,
        "staticmethod": staticmethod,
        "property": property,
        "getattr": getattr,
        "setattr": setattr,
        "dict": dict
    },

    # discord API
    "discord": _SafeEnvObject(_SafeDiscordApi),
    "app_commands": _SafeEnvObject(
        discord.app_commands, include_all=False,
        command=True,
        describe=True
    ),
    "ui": _SafeEnvObject(discord.ui),
    # discord cogs
    "Cog": commands.Cog,
    "Group": commands.Group,
    "GroupCog": commands.GroupCog,

    # modules
    "datetime": _SafeEnvObject(datetime),
    "asyncio": _SafeEnvObject(asyncio),
    "random": _SafeEnvObject(random),
    "json": json,

    # types
    "Any": Any,
    "Callable": Callable,
    "Optional": Optional,
    # enum
    "Enum": Enum,
    "auto": auto,
    # loguru
    "logger": logger,

    # script bot env
    "ScriptDatabase": _SafeEnvObject(_SafeDataBase),
    "ScriptGuild": _SafeEnvObject(_ScriptGuild),
    "Bot": _SafeEnvObject(_SafeBot),

    # safe functions
    "calculate": calculate,
    "iterate": iterate
}


class BaseScript(ABC):
    lang = None

    def __init_subclass__(cls, **kwargs):
        _script_types[cls.lang] = cls
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_type(cls, script_lang) -> Type['BaseScript'] | None:
        return _script_types.get(script_lang)

    def __init__(self, engine: 'bot.ScriptEngine', guild_id: int, code: str, name: str, is_lib: bool):
        self.engine: bot.ScriptEngine = engine

        self.guild_id = guild_id
        self.name = name

        self.filename = f"{guild_id}\\{name}"
        self.code: str = code

        self.compiled_code: Optional[str] = None
        self.code_env: dict[str, Any] = dict()
        self.is_lib = is_lib

        for name, value in {
            **_static_script_env,
            "guild_id": guild_id,
            "include": self.include
        }.items():
            self.code_env[name] = value

        self.main_func: Optional[Callable] = None

    def include(self, module_name: str, as_name: Optional[str] = None) -> None:
        module_name = module_name.replace("lib.", "")

        if module_name == self.name:
            raise ValueError(f"Cannot include self: {module_name}")

        script = self.engine.get_script(self.guild_id, module_name, get_default=True)

        if not script:
            raise ImportError(f"Script {module_name} not found")

        self.code_env.update(
            {as_name or module_name: _EnvObject(script.code_env)}
        )
        return

    @property
    def env_guild_id(self) -> str:
        return self.code_env["guild_id"]

    @env_guild_id.setter
    def env_guild_id(self, value: int) -> None:
        self.code_env["guild_id"] = value

    async def execute_main_func(self, context: dict):
        return await self.main_func(**(await self.create_safe_context(context)))

    def _update_main_func(self) -> Callable:
        try:
            self.main_func = self.code_env["main"]
        except (AttributeError, KeyError) as e:
            raise AttributeError(f"Code not implement enter point: {str(e)}")
        finally:
            if not asyncio.iscoroutinefunction(self.main_func):
                raise TypeError("Main function must be async")

    async def create_safe_context(self, context: dict) -> dict:
        context["bot"] = _SafeEnvObject(_SafeBot(
            self.engine.bot.user,
            _SafeEnvObject(_ScriptGuild(
                self.engine,
                _SafeEnvObject(_SafeDataBase(
                    await GuardDatabase.get_server(guild_id=self.env_guild_id)
                )),
                guild_id=self.env_guild_id
            ))
        ))

        if msg := context.get("msg"):
            context["msg"] = _SafeEnvObject(msg, interaction=False)
        if member := context.get("member"):
            context["member"] = _SafeEnvObject(member, interaction=False)
        if guild := context.get("guild"):
            context["guild"] = _SafeEnvObject(guild, interaction=False)

        return context

    @abstractmethod
    def compile(self) -> Self:
        pass

    async def execute(self, guild_id: int, **context: Any) -> Any:
        self.env_guild_id = guild_id

        try:
            return await asyncio.wait_for(
                self.execute_main_func(context),
                timeout=self.engine.script_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Script {self.filename} timeout: {self.engine.script_timeout}s")
            raise

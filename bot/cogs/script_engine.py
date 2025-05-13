from typing import Any, Type, Callable
from abc import ABC, abstractmethod
from pathlib import Path
import math
import ast
import asyncio

from discord.ext import commands

import lupa
from loguru import logger

from bot.bot import GuardBot
from bot.database import GuardDatabase


class BaseScript(ABC):
    """Абстрактный базовый класс для скриптов"""

    def __init__(self, engine: 'ScriptEngine', code_env: dict | object):
        self.engine: ScriptEngine = engine
        self.code_env: dict | object = code_env
        self.main_func = self._get_main_func()

    def __getitem__(self, item: str) -> Any:
        try:
            if isinstance(self.code_env, dict):
                return self.code_env[item]
            return getattr(self.code_env, item)
        except Exception as e:
            raise AttributeError(f"Cant find item in script env: {str(e)}")

    def _get_main_func(self) -> Callable:
        try:
            return self["main"]
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

    def create_safe_context(self, context: dict) -> dict:
        context["bot"] = self.engine.bot

        return context

    @classmethod
    @abstractmethod
    def compile(cls, content: str, engine: 'ScriptEngine') -> 'BaseScript':
        pass

    @abstractmethod
    async def execute(self, context: dict) -> Any:
        pass


class LuaScript(BaseScript):
    """Обработчик Lua-скриптов"""

    @classmethod
    def compile(cls, content: str, engine: 'ScriptEngine') -> 'LuaScript':
        lua_env = engine.lua_runtime.table()
        lua_env.calculate = cls.safe_calculate

        loader = engine.lua_runtime.eval('''
            function(env, code)
                local chunk, err = load(code, nil, 't', env)
                if not chunk then return nil, err end
                return chunk()
            end
        ''')

        success, result = loader(lua_env, content)
        if not success:
            raise RuntimeError(f"Lua error: {result}")

        return cls(engine, lua_env)

    async def execute(self, context: dict) -> Any:
        return await asyncio.to_thread(
            self.main_func,
            **self.create_safe_context(context)
        )


class PythonScript(BaseScript):
    """Обработчик Python-скриптов"""

    @staticmethod
    def _validate_syntax(code: str) -> None:
        """AST-валидация кода"""
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.ImportFrom):
                if node.module == 'bot.script_deps' and not any(name.name == '*' for name in node.names):
                    continue
                raise SyntaxError(f"Недопустимый импорт: {node.module}")
            elif isinstance(node, ast.Import):
                raise SyntaxError("Прямые импорты запрещены")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    raise SyntaxError("Использование print запрещено")

    @classmethod
    def compile(cls, content: str, engine: 'ScriptEngine') -> 'PythonScript':
        py_env = {
            "calculate": cls.safe_calculate
        }
        exec(content, py_env)
        return cls(engine, py_env)

    async def execute(self, context: dict) -> Any:
        return await self.main_func(**self.create_safe_context(context))


class ScriptEngine(commands.Cog):
    """Ядро системы управления скриптами"""

    def __init__(
            self, bot, scripts_dir="scripts", /,
            lua_runtime: lupa.LuaRuntime = lupa.LuaRuntime(),
            script_timeout: int = 30
    ):
        self.bot = bot
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
                    logger.error(f"Failed to load {script_path.name}: {e}")
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
        script = script_type.compile(content, self)
        return {name: script}

    async def get_script(self, guild_id: int, name: str) -> BaseScript:
        script = self.scripts[guild_id].get(name)
        if not script:
            script = self.scripts[None].get(name)
        return script

    async def execute(self, name: str, guild_id: int | None, **context) -> Any:
        """Запуск скрипта по имени"""
        if script := await self.get_script(guild_id, name):
            try:
                return await script.execute(context)
            except Exception as e:
                logger.exception(f"Script error in {name}: {e}")
                raise
        return None


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptEngine loading")
    await bot.add_cog(ScriptEngine(bot))

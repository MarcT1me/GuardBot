from abc import ABC, abstractmethod
import asyncio
from pathlib import Path

from discord.ext import commands

import lupa
from loguru import logger

from bot_core.bot import GuardBot


class BaseScript(ABC):
    """Абстрактный базовый класс для скриптов"""

    def __init__(self, engine, main_func):
        self.engine = engine
        self.main_func = main_func

    @classmethod
    @abstractmethod
    def compile(cls, content: str, path: Path, engine: 'ScriptEngine') -> 'BaseScript':
        pass

    @abstractmethod
    async def execute(self, context: dict) -> any:
        pass


class LuaScript(BaseScript):
    """Обработчик Lua-скриптов"""

    def __init__(self, engine, main_func, lua_env):
        super().__init__(engine, main_func)
        self.lua_env = lua_env

    @classmethod
    def compile(cls, content: str, path: Path, engine: 'ScriptEngine') -> 'LuaScript':
        lua_env = engine.lua_runtime.table()
        lua_env.bot = engine.bot
        lua_env.engine = engine

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

        return cls(engine, lua_env.main, lua_env)

    async def execute(self, context: dict) -> any:
        return await asyncio.to_thread(
            self.main_func,
            self.lua_env.table(self.engine.bot, **context)
        )


class PythonScript(BaseScript):
    """Обработчик Python-скриптов"""

    @classmethod
    def compile(cls, content: str, path: Path, engine: 'ScriptEngine') -> 'PythonScript':
        exec_globals = {"bot": engine.bot, "engine": engine}
        code = compile(content, path.name, 'exec')
        exec(code, exec_globals)
        return cls(engine, exec_globals.get('main'))

    async def execute(self, context: dict) -> any:
        return await self.main_func(self.engine.bot, **context)


class ScriptEngine(commands.Cog):
    """Ядро системы управления скриптами"""

    def __init__(self, bot, scripts_dir="scripts"):
        self.bot = bot
        self.lua_runtime = lupa.LuaRuntime()
        self.scripts: dict[str, BaseScript] = {}
        self._load_scripts(Path(scripts_dir))

    def _load_scripts(self, scripts_dir: Path):
        """Рекурсивная загрузка скриптов из директории"""
        for script_file in scripts_dir.glob("**/*"):
            if script_file.is_file() and script_file.suffix in ('.lua', '.py'):
                self._compile_script(script_file)

    def _compile_script(self, path: Path):
        """Компиляция отдельного скрипта"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            compiler = LuaScript if path.suffix == '.lua' else PythonScript
            script = compiler.compile(content, path, self)
            self.scripts[path.stem] = script
            logger.success(f"Script loaded: {path.stem}")

        except Exception as e:
            logger.error(f"Failed to load {path.name}: {e}")

    async def execute(self, name: str, **context) -> any:
        """Запуск скрипта по имени"""
        if script := self.scripts.get(name):
            try:
                return await script.execute(context)
            except Exception as e:
                logger.error(f"Script error in {name}: {e}")
        return None


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptEngine loading")
    await bot.add_cog(ScriptEngine(bot))

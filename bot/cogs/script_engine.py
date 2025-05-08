from typing import Any, Type
from abc import ABC, abstractmethod
from pathlib import Path

from discord.ext import commands

import lupa
import docker
import asyncio

from loguru import logger

from bot.bot import GuardBot
from bot.database import Server


class BaseScript(ABC):
    """Абстрактный базовый класс для скриптов"""

    def __init__(self, engine, main_func):
        self.engine = engine
        self.main_func = main_func

    @classmethod
    @abstractmethod
    def compile(cls, content: str, engine: 'ScriptEngine') -> 'BaseScript':
        pass

    async def execute(self, context: dict) -> Any:
        return await asyncio.to_thread(
            self.main_func,
            **context
        )


class LuaScript(BaseScript):
    """Обработчик Lua-скриптов"""

    def __init__(self, engine, main_func, lua_env):
        super().__init__(engine, main_func)
        self.lua_env = lua_env

    @classmethod
    def compile(cls, content: str, engine: 'ScriptEngine') -> 'LuaScript':
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


class PythonScript(BaseScript):
    """Обработчик Python-скриптов"""

    @classmethod
    def compile(cls, content: str, engine: 'ScriptEngine') -> 'PythonScript':
        exec_globals = {"bot": engine.bot, "engine": engine}
        exec(content, exec_globals)
        return cls(engine, exec_globals.get('main'))


class ScriptEngine(commands.Cog):
    """Ядро системы управления скриптами"""

    def __init__(
            self, bot, scripts_dir="scripts", /,
            lua_runtime: lupa.LuaRuntime = lupa.LuaRuntime(),
            docker_client: docker.DockerClient = docker.from_env(),
            script_timeout: int = 30
    ):
        self.bot = bot
        self.scripts_dir = scripts_dir
        self.lua_runtime = lua_runtime

        self._scripts_cache: dict[int | None, dict[str, BaseScript]] = {}

        self.docker_client = docker_client
        self.script_timeout = script_timeout

    async def _get_server_scripts(self, guild_id: int) -> dict:
        if guild_id not in self._scripts_cache:
            server, _ = await self.bot.db.get_server(guild_id)
            self._scripts_cache[guild_id] = {
                script.name: script
                for script in await server.scripts.filter(is_active=True)
            }

    @commands.Cog.listener()
    async def on_ready(self):
        await self._load_scripts_from_db()
        self._load_scripts_from_dir(Path(self.scripts_dir))

    async def _load_scripts_from_db(self):
        servers = await Server.all().prefetch_related('scripts')
        for server in servers:
            _scripts_cache = {
                script.name: script.content
                for script in server.scripts.filter(is_active=True)
            }

            # self._compile_and_save_script(
            #     LuaScript if script_path.suffix == '.lua' else PythonScript,
            #     script_path.stem,
            #     content,
            #     None
            # )
            #
            # logger.success(f"Script loaded: {script_path.stem}")

    def _load_scripts_from_dir(self, scripts_dir: Path):
        """Рекурсивная загрузка скриптов из директории"""
        for script_path in scripts_dir.glob("**/*"):
            if script_path.is_file() and script_path.suffix in ('.lua', '.py'):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    self._compile_and_save_script(
                        LuaScript if script_path.suffix == '.lua' else PythonScript,
                        script_path.stem,
                        content,
                        None
                    )

                    logger.success(f"Script loaded: {script_path.stem}")
                except Exception as e:
                    logger.error(f"Failed to load {script_path.name}: {e}")

    def _compile_and_save_script(
            self,
            compiler: Type[BaseScript],
            name: str,
            content: Path,
            guild_id: int | None
    ):
        """Компиляция отдельного скрипта"""
        script = compiler.compile(content, self)
        self._scripts_cache[guild_id] = {name: script}

    async def execute(self, name: str, guild_id: int | None, **context) -> any:
        """Запуск скрипта по имени"""
        context["bot"] = self.bot  # Добавляем бота в контекст
        if script := self._scripts_cache[guild_id].get(name):
            try:
                return await script.execute(context)
            except Exception as e:
                logger.error(f"Script error in {name}: {e}")
        return None


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptEngine loading")
    await bot.add_cog(ScriptEngine(bot))

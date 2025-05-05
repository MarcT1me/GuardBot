import asyncio
from pathlib import Path

from loguru import logger
import lupa


class ScriptEngine:
    def __init__(self, bot, scripts_dir="scripts"):
        self.bot = bot
        self.scripts_dir = Path(scripts_dir)
        self.lua = lupa.LuaRuntime()
        self.scripts = {}
        self.callbacks = {}

        self._load_scripts()

    def _load_scripts(self):
        """Загрузка и компиляция скриптов из папки"""
        for script_file in self.scripts_dir.glob("**/*"):
            if script_file.suffix in ('.lua', '.py'):
                self._compile_script(script_file)

    def _compile_script(self, path):
        """Обработка скриптов разных типов"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            script_name = path.stem
            if path.suffix == '.lua':
                self.scripts[script_name] = {
                    'type': 'lua',
                    'code': self.lua.eval(content)
                }
            else:
                self.scripts[script_name] = {
                    'type': 'python',
                    'code': compile(content, path.name, 'exec')
                }

            logger.success(f"Script loaded: {script_name}")
        except Exception as e:
            logger.error(f"Failed to load {path.name}: {e}")

    async def execute(self, name: str, **context):
        """Запуск скрипта по имени"""
        script = self.scripts.get(name)
        if not script:
            return None

        try:
            if script['type'] == 'lua':
                return await self._run_lua(script['code'], context)
            return await self._run_python(script['code'], context)
        except Exception as e:
            logger.error(f"Script error in {name}: {e}")
            return None

    async def _run_lua(self, code, ctx):
        """Выполнение Lua скрипта"""
        lua_func = code
        lua_ctx = self.lua.table(bot=self.bot, engine=self, **ctx)
        return await asyncio.to_thread(lua_func, lua_ctx)

    async def _run_python(self, code, ctx):
        """Выполнение Python скрипта"""
        exec_globals = {
            "bot": self.bot,
            "engine": self,
        }
        exec(code, exec_globals)
        return exec_globals.get('main')(bot=self.bot, engine=self, **ctx)

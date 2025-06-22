import asyncio
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from lupa.lua54 import LuaRuntime

from bot.bot import GuardBot, GuardDatabase
from bot.cogs.script_engine.scripts import BaseScript


class ScriptEngine:
    """Ядро системы управления скриптами"""
    async_events: dict[int, dict[str, asyncio.Event]] = {}

    def __init__(
            self, bot: GuardBot, lua_runtime: LuaRuntime, /,
            scripts_dir="scripts",
            lib_dir="scripts/lib",
            script_timeout: int = 30
    ):
        self.bot: GuardBot = bot
        self.scripts_dir: Path = Path(scripts_dir)
        self.lib_dir: Path = Path(lib_dir)
        self.lua_runtime: LuaRuntime = lua_runtime

        self.scripts: dict[int | None, dict[str, BaseScript]] = {
            None: {}
        }

        self.script_timeout = script_timeout

    async def load_scripts(self) -> None:
        logger.debug("Loading scripts")

        self.scripts[None].update(
            self._compile_to_cache(
                None,
                "py",
                "EMPTY_LIB",
                "",
                True
            )
        )
        await self.load_scripts_from_dir()
        await self.load_scripts_from_db()

    async def guilds_on_ready(self) -> None:
        logger.info("setup on_ready.data for guilds\n")

        for guild in self.bot.guilds:
            script_name, guild_id = await self.get_event_script(None, "on_ready")
            await self.execute(
                script_name,
                guild_id,
                guild.id,
                guild=guild
            )
            logger.success(f"`{guild}` data ready\n")

    async def get_event_script(self, guild, event_name: str) -> tuple[GuardDatabase.script, int]:
        if not guild:
            return event_name, None

        server = await self.bot.db.get_server(guild_id=guild.id)
        script = await self.bot.db.get_script(
            server=server, script_type="py\\event", script_name=event_name
        ) or await self.bot.db.get_script(
            server=server, script_type="lua\\event", script_name=event_name
        )

        if script:
            return script.name, guild.id
        else:
            return event_name, None

    async def load_scripts_from_db(self) -> list:
        load_errors = []

        scripts: list[GuardDatabase.script] = await GuardDatabase.script.filter(is_active=True)

        for i, script in enumerate(scripts):
            if "lib" in script.type:
                try:
                    lang, script_type, script_gild_id = await self._init_db_script_cache(script)

                    self.scripts[script_gild_id].update(
                        self._compile_to_cache(
                            script_gild_id,
                            lang,
                            script.name,
                            script.content,
                            script_type == "lib"
                        )
                    )

                    logger.success(f"Library loaded: {script.name}")
                except Exception as e:
                    logger.error(f"Failed to fetch {script.name}: {e}")
                    load_errors.append(
                        (e, f"Failed to fetch {script.name}: {e}")
                    )

        for script in scripts:
            if "lib" not in script.type:
                try:
                    lang, script_type, script_gild_id = await self._init_db_script_cache(script)

                    self.scripts[script_gild_id].update(
                        self._compile_to_cache(
                            script_gild_id,
                            lang,
                            script.name,
                            script.content,
                            script_type == "lib"
                        )
                    )

                    logger.success(f"Script loaded: {script.name}")

                except Exception as e:
                    logger.exception(f"Failed to fetch {script.name}: {e}")
                    load_errors.append(
                        (e, f"Failed to fetch {script.name}: {e}")
                    )

        return load_errors

    async def _init_db_script_cache(self, script: GuardDatabase.script) -> tuple[str, str, int]:
        lang, script_type = script.type.split("\\")
        script_gild_id = (await script.server.values("guild_id"))["guild_id"]
        if script_gild_id not in self.scripts: self.scripts[script_gild_id] = {}
        return lang, script_type, script_gild_id

    async def load_scripts_from_dir(self) -> None:
        """Рекурсивная загрузка скриптов из директории"""
        load_errors = []

        is_script_file = lambda path: path.is_file() and path.suffix in ('.py', '.lua')

        for lib_path in self.lib_dir.glob("*"):
            if is_script_file(lib_path):
                try:
                    with open(lib_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    self.scripts[None].update(
                        self._compile_to_cache(
                            None,
                            lib_path.suffix[1:],  # + "\\lib",
                            lib_path.stem,
                            content,
                            True
                        )
                    )

                    logger.success(f"Library loaded: {lib_path.stem}")
                except Exception as e:
                    logger.exception(f"Failed to load lib.{lib_path.name}: {e}")
                    load_errors.append(
                        (e, f"Failed to load lib.{lib_path.name}: {e}")
                    )

        for script_path in self.scripts_dir.glob("*"):
            if is_script_file(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    script_name: str = script_path.stem
                    self.scripts[None].update(
                        self._compile_to_cache(
                            None,
                            script_path.suffix[1:],
                            # + "\\" + ("event" if script_name.startswith("on_") else "default"),
                            script_name,
                            content,
                            False
                        )
                    )

                    logger.success(f"Script loaded: {script_path.stem}")
                except Exception as e:
                    logger.exception(f"Failed to load {script_path.name}: {e}")
                    load_errors.append(
                        (e, f"Failed to load {script_path.name}: {e}")
                    )

        return load_errors

    def _add_default_script(self, guild_id: int, name: str) -> None:
        self.scripts[guild_id].update({
            name: self.scripts[None]["EMPTY_LIB"]
        })

    def _compile_to_cache(
            self, guild_id: int, script_lang: str, name: str, content: str, is_lib
    ) -> dict[str, BaseScript]:
        return {name: self.compile(guild_id, script_lang, name, content, is_lib)}

    def compile(self, guild_id: int, script_lang: str, name: str, content: str, is_lib: bool) -> BaseScript:
        try:
            return BaseScript.get_type(script_lang)(self, guild_id, content, name, is_lib).compile()
        except Exception:
            raise RuntimeError(f"Any error in {name} compilation process")

    async def execute(
            self, name: str, script_guild_id: Optional[int], guild_id: int, **context
    ) -> Any:
        """Запуск скрипта по имени"""
        if script := self.get_script(script_guild_id, name):
            return await self.execute_script(script, guild_id, **context)
        return logger.error(f"Script {name} not found")

    def get_script(self, guild_id: int, name: str) -> BaseScript | None:
        script_field = self.scripts.get(guild_id)
        if not script_field:
            logger.warning("cant find guild script, use default")
            script_field = self.scripts[None]

        script = script_field.get(name)
        return script

    async def fast_execute(
            self, lang: str, content: str, guild_id: int,
            env: dict, **context
    ) -> tuple[BaseScript, Any]:
        """Запуск скрипта по имени"""
        script: BaseScript = self.compile(guild_id, lang, "<fast_script>", content, False)
        script.code_env.update(**env)
        return script, await self.execute_script(script, guild_id, **context)

    @staticmethod
    async def execute_script(
            script: BaseScript, guild_id: int, **context
    ) -> Any:
        try:
            ret = await script.execute(guild_id, **context)
            return ret
        except Exception as e:
            logger.exception(f"Error in script {script.filename}: {e}")
            raise

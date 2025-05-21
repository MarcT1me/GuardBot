import asyncio
import datetime
import json
from pprint import pformat

import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger
from lupa.lua54 import LuaRuntime

from bot.bot import GuardBot
from bot.cogs.script_engine import ScriptEngine


class ExecutorSeance:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.env: dict = {}
        self.clear_env()

    def expand_env(self, **context) -> dict:
        self.env.update(**context)
        return self.env

    def clear_env(self) -> None:
        self.env = {
            "response": self.response,
            "flush_response": self.flush_response,
            "__std_send_response_message__": ""
        }

    def response(self, *args, sep: str = " ", end: str = "\n") -> None:
        self.env["__std_send_response_message__"] += sep.join([str(arg) for arg in args]) + end

    def clear_response(self) -> None:
        self.env["__std_send_response_message__"] = ""

    async def flush_response(self) -> None:
        await self.env["send"](
            f"{datetime.datetime.now().ctime()} | ```\n{self.env["__std_send_response_message__"]}\n```"
        )
        self.clear_response()

    async def execute(self, lang: str, code: str, guild_id: int, **context) -> any:
        try:
            script, ret = await self.bot.script_eng.fast_execute(lang, code, guild_id, self.env, **context)
            self.expand_env(**script.code_env)

            self.clear_response()
            return ret
        except Exception as e:
            logger.exception(f"{e}")
            return e
        except RuntimeWarning as e:
            logger.exception(f"{e}")
            return e


class ExecutorManager:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.seances: dict[int, ExecutorSeance] = {}

    def get_seance(self, user: discord.User) -> ExecutorSeance | None:
        return self.seances.get(user.id)

    def seance(self, user: discord.User):
        if user.id in self.seances:
            return self.get_seance(user)
        return self.create_seance(user)

    def create_seance(self, user: discord.User) -> ExecutorSeance:
        seance = ExecutorSeance(self.bot)
        self.seances[user.id] = seance
        return seance

    def delete_seance(self, user: discord.User) -> ExecutorSeance:
        return self.seances.pop(user.id)


class ScriptCog(commands.Cog):
    """Ядро системы управления скриптами"""
    async_events: dict[int, dict[str, asyncio.Event]] = {}

    def __init__(
            self, bot: GuardBot, engine: ScriptEngine
    ):
        self.bot: GuardBot = bot
        self.engine: ScriptEngine = engine

        self.manager = ExecutorManager(bot)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async with self.bot.wait_for_cog_loading(0):
            await self.engine.load_scripts()
            await self.engine.guilds_on_ready()

    @app_commands.command(
        name="update_scripts",
        description="обновляет скрипты"
    )
    @app_commands.describe(
        from_db="если команда вызвана с сервера можно обновить guild скрипты",
    )
    @GuardBot.error_handler(is_defer=True)
    async def update_scripts(self, interaction: discord.Interaction, from_db: bool = False):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        await interaction.response.defer()  # type: ignore

        try:
            logger.debug("Scripts reloading")
            if from_db:
                error_list = await self.bot.script_eng.load_scripts_from_db()
            else:
                error_list = await self.bot.script_eng.load_scripts_from_dir()

            if not error_list:
                await interaction.followup.send(  # type: ignore
                    "✅ Success"
                )
            else:
                error_messages = ""
                for e, description in error_list:
                    error_messages += "\n" + description

                await interaction.followup.send(  # type: ignore
                    "⚠️ Any error(s):" + error_messages
                )
        except Exception as e:
            await interaction.followup.send(  # type: ignore
                f"⚠️ Unexpected error: {e}"
            )
            raise

    @app_commands.command(
        name="exec_mode",
        description="переключатель для выполнения скрипта из чата"
    )
    @app_commands.describe(
        status="на какой статус переключиться",
    )
    @GuardBot.error_handler()
    async def exec_mode(self, interaction: discord.Interaction, status: bool):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        if status:
            self.manager.create_seance(interaction.user)
            await interaction.response.send_message(  # type: ignore
                "▶️ Execution - on"
            )
        else:
            if self.manager.get_seance(interaction.user):
                self.manager.delete_seance(interaction.user)
            await interaction.response.send_message(  # type: ignore
                "⏹️ Execution - off"
            )

    @app_commands.command(
        name="exec_mode_status",
        description="показывает в активность команды exec_mode"
    )
    @GuardBot.error_handler()
    async def exec_mode_status(self, interaction: discord.Interaction):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        if self.manager.get_seance(interaction.user):
            await interaction.response.send_message(  # type: ignore
                "▶️ Now execution - on"
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⏹️ Now execution - off"
            )

    @app_commands.command(
        name="exec_script",
        description="выполняет скрипт"
    )
    @app_commands.describe(
        script_name="имя скрипта",
        from_db="если команда вызвана с сервера можно выполнить guild скрипт",
        kwargs="аргументы для скрипта в формате json"
    )
    @GuardBot.error_handler(is_defer=True)
    async def exec_script(
            self, interaction: discord.Interaction,
            script_name: str,
            from_db: bool = False,
            kwargs: str = "{}"
    ):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        await interaction.response.defer()  # type: ignore

        try:
            ret = await self.bot.script_eng.execute(
                script_name, interaction.guild_id if from_db else None,
                interaction=interaction,
                **json.loads(kwargs)
            )
            await interaction.followup.send(  # type: ignore
                "Result:\n"
                "```\n"
                f"{pformat(ret)}\n"
                "```\n"
            )
        except Exception as e:
            await interaction.followup.send(  # type: ignore
                f"Критичная ошибка при выполнении: {e}"
            )
            raise
        except RuntimeWarning as e:
            await interaction.followup.send(  # type: ignore
                f"Ошибка при выполнении: {e}"
            )
            raise

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if seance := self.manager.get_seance(msg.author):
            content = msg.content

            if content.startswith("```python") or content.startswith("```lua"):
                code = content
                code, lang = (code.replace("```lua", ""), "lua") \
                    if content.startswith("```lua") \
                    else (code.replace("```python", ""), "py")
                code = code.replace("```", "")

                try:
                    seance.expand_env(
                        send=msg.channel.send
                    )
                    result = await seance.execute(
                        lang,
                        code,
                        msg.guild.id,
                        full_bot = self.bot,
                        msg=msg
                    )

                    response = (
                            (
                                "Error:\n"
                                if isinstance(result, Exception) else
                                "Result:\n"
                            ) +
                            "```python\n"
                            f"{pformat(result)}\n"
                            "```"
                    )

                    await msg.channel.send(
                        GuardBot.normalize_response_size(response, end="\n```")
                    )
                except Exception as e:
                    logger.exception("Error in script")

                    await msg.channel.send(
                        "Error:\n" + str(e)
                    )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptCog loading")
    await bot.add_cog(
        ScriptCog(
            bot,
            ScriptEngine(bot, LuaRuntime(), script_timeout=600)
        )
    )

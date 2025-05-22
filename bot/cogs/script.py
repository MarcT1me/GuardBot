import asyncio
import datetime
import json
from pprint import pformat

import discord
from discord import app_commands
from discord import ui
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

    @app_commands.command(
        name="script_hub",
        description="Команды скрипт системы"
    )
    async def script_hub(self, interaction: discord.Interaction):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬",
                ephemeral=True
            )

        view = ScriptView(self, interaction.user)

        await interaction.response.send_message(  # type: ignore
            "**Панель управления Скриптами**\n"
            "Выберите действие:",
            view=view,
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async with self.bot.wait_for_cog_loading(0):
            await self.engine.load_scripts()
            await self.engine.guilds_on_ready()

    @GuardBot.error_handler(is_defer=True)
    async def update_scripts(self, interaction: discord.Interaction, from_db: bool = False):
        try:
            logger.debug("Scripts reloading")
            if from_db:
                error_list = await self.bot.script_eng.load_scripts_from_db()
            else:
                error_list = await self.bot.script_eng.load_scripts_from_dir()

            if not error_list:
                await interaction.followup.send(  # type: ignore
                    "✅ Success updated",
                    ephemeral=True
                )
            else:
                error_messages = ""
                for e, description in error_list:
                    error_messages += "\n" + description

                await interaction.followup.send(  # type: ignore
                    "⚠️ Any error(s) in updating process:" + error_messages,
                    ephemeral=True
                )
        except Exception as e:
            await interaction.followup.send(  # type: ignore
                f"⚠️ Unexpected error in updating process: {e}",
                ephemeral=True
            )
            raise

    @GuardBot.error_handler()
    async def turn_exec_mode(self, interaction: discord.Interaction) -> bool:
        if self.manager.get_seance(interaction.user):
            self.manager.delete_seance(interaction.user)
        else:
            self.manager.create_seance(interaction.user)

    @GuardBot.error_handler(is_defer=True)
    async def exec_script(
            self, interaction: discord.Interaction,
            script_name: str,
            from_db: bool = False,
            kwargs: str = "{}"
    ):
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
                "```\n",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(  # type: ignore
                f"⚠️ Критичная ошибка при выполнении: {e}",
                ephemeral=True
            )
            raise
        except RuntimeWarning as e:
            await interaction.followup.send(  # type: ignore
                f"⚠️ Ошибка при выполнении: {e}",
                ephemeral=True
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
                        full_bot=self.bot,
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


class ScriptView(ui.View):
    def __init__(self, cog: ScriptCog, user: discord.User):
        super().__init__(timeout=None)
        self.cog: ScriptCog = cog
        self._update_buttons(user)

    @ui.button(label="Turn exec mode", style=discord.ButtonStyle.secondary, custom_id="script:toggle_exec")
    async def turn_exec_mode(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use turn_exec_mode")

        await self.cog.turn_exec_mode(interaction)
        self._update_buttons(interaction.user)
        await interaction.response.edit_message(view=self)  # type: ignore

    def _update_buttons(self, user: discord.User):
        session = self.cog.manager.get_seance(user)
        self.turn_exec_mode.label = "⏹️ Остановить" if session else "▶️ Запустить"
        self.turn_exec_mode.style = discord.ButtonStyle.red if session else discord.ButtonStyle.green

    @ui.button(label="♻️ Обновить скрипты", style=discord.ButtonStyle.secondary, custom_id="script:update")
    async def update_scripts(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use update_scripts")

        await interaction.response.send_modal(  # type: ignore
            UpdateScriptsModal(self.cog)
        )

    @ui.button(label="⚡ Выполнить скрипт", style=discord.ButtonStyle.blurple, custom_id="script:exec")
    async def exec_script(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use exec_script")

        await interaction.response.send_modal(  # type: ignore
            ExecuteScriptModal(self.cog)
        )


class UpdateScriptsModal(ui.Modal, title="Обновление скриптов"):
    from_db = ui.TextInput(
        label="Обновить guild скрипт",
        placeholder="True для активации",
        required=False
    )

    def __init__(self, cog: ScriptCog):
        super().__init__()
        self.cog: ScriptCog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # type: ignore
        from_db = self.from_db.value == "True"

        await self.cog.update_scripts(interaction, from_db)


class ExecuteScriptModal(ui.Modal, title="Выполнение скриптов"):
    name = ui.TextInput(
        label="Имя скрипта",
        placeholder="Пример: add_guild_to_db",
        required=True
    )
    kwargs = ui.TextInput(
        label="аргументы скрипта (JSON format)",
        default="{}",
        required=False,
    )
    from_db = ui.TextInput(
        label="Использовать guild скрипт",
        placeholder="True для активации",
        required=False
    )

    def __init__(self, cog: ScriptCog):
        super().__init__()
        self.cog: ScriptCog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # type: ignore
        from_db = self.from_db.value == "True"

        await self.cog.exec_script(interaction, self.name.value, from_db, self.kwargs.value)


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ScriptCog loading")
    await bot.add_cog(
        ScriptCog(
            bot,
            ScriptEngine(bot, LuaRuntime(), script_timeout=600)
        )
    )

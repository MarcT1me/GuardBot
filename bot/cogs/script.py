import asyncio
import datetime
import json
from pprint import pformat
from typing import Any, Optional
from io import BytesIO

import discord
from discord import app_commands
from discord import ui
from discord.ext import commands
from loguru import logger
from lupa.lua54 import LuaRuntime

from bot import GuardBot, GuardDatabase
from bot.cogs.script_engine import ExecutorManager, ScriptEngine, scripts


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
    async def script_hub(self, interaction: discord.Interaction, is_light: bool = True):
        view = None

        if await self.bot.check_botdev(interaction):
            if is_light:
                view = LightScriptView(self)
            else:
                view = ScriptView(self, interaction.user)


        elif user := await self.bot.db.get_user(
                server=await self.bot.db.get_server(guild_id=interaction.guild_id),
                user_id=interaction.user.id
        ):
            if user.additions.get("allow_scripts"):
                view = LightScriptView(self)

        if view:
            await interaction.response.send_message(  # type: ignore
                "**Панель управления Скриптами**\n"
                "Выберите действие:",
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬",
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
                script_name, interaction.guild_id if from_db else None, interaction.guild_id,
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


class LightScriptView(ui.View):
    def __init__(self, cog: ScriptCog):
        super().__init__()
        self.cog: ScriptCog = cog

    @ui.button(label="❔ просмотр скриптов", style=discord.ButtonStyle.secondary, custom_id="light_script:check")
    async def check_scripts(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use light_script:check")

        view = CheckScriptsView(self.cog)

        await interaction.response.send_message(  # type: ignore
            "Настройте фильтры и выполните поиск",
            view=view,
            ephemeral=True
        )

    @ui.button(label="♻️ Обновить скрипты", style=discord.ButtonStyle.secondary, custom_id="light_script:update")
    async def update_scripts(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use light_script:update")
        await interaction.response.defer(ephemeral=True)  # type: ignore

        await self.cog.update_scripts(interaction, True)

    @ui.button(label="⚡ Выполнить скрипт", style=discord.ButtonStyle.blurple, custom_id="light_script:exec")
    async def exec_script(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use light_script:exec")

        await interaction.response.send_modal(  # type: ignore
            ExecuteScriptModal(self.cog)
        )

    @ui.button(label="🚀 on guild", style=discord.ButtonStyle.primary, custom_id="hub:bot_on_guild")
    @app_commands.guild_only
    async def bot_on_guild(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()  # type: ignore
        await self.cog.engine.guild_on_ready(interaction.guild)
        await interaction.followup.send("✅ Success", ephemeral=True)  # type: ignore


class CheckScriptsView(ui.View):
    _options = [
        discord.SelectOption(label="Python", value="py", description="написанные на Python", default=False),
        discord.SelectOption(label="Lua", value="lua", description="написанные на Lua", default=False),
        discord.SelectOption(label="libs", value="lib", description="библиотеки (зависимости)", default=False),
        discord.SelectOption(label="events", value="event", description="автоматические события", default=False),
        discord.SelectOption(label="defaults", value="default", description="вызываемые функции", default=False),
    ]
    _max_values = len(_options) - 1

    def __init__(self, cog: ScriptCog):
        super().__init__()
        self.cog: ScriptCog = cog

    @ui.select(
        cls=ui.Select,
        placeholder="Выберите фильтры",
        options=_options,
        max_values=_max_values,
        custom_id="script_check:filter_select_check"
    )
    async def check_scripts(self, interaction: discord.Interaction, filter_select: ui.Select):
        await interaction.response.defer(ephemeral=True)  # type: ignore
        selected_filters = filter_select.values  # Получаем выбранные значения

        if "all" in selected_filters:
            selected_filters = ["py", "lua"]

        db_server: GuardDatabase.server = await self.cog.bot.db.get_server(guild_id=interaction.guild_id)
        db_scripts: set[GuardDatabase.script] = await self.cog.bot.db.script.filter(server=db_server)
        eng_scripts: dict[str, scripts.BaseScript] = self.cog.bot.script_eng.scripts.get(interaction.guild_id)

        if not any(
                filter in db_script.type
                for filter in selected_filters
                for db_script in db_scripts
        ):
            await interaction.followup.send(  # type: ignore
                "Я не нашёл скриптов подходящих под фильтры",
                ephemeral=True
            )

        err_list = []

        for db_script in db_scripts:
            try:
                if any(
                        filter in db_script.type
                        for filter in selected_filters
                ):
                    script_params: dict[str, Any] = await self._get_script_params(
                        db_script,
                        eng_scripts.get(db_script.name)
                    )

                    await interaction.followup.send(  # type: ignore
                        embed=await self._get_embed(
                            script_params
                        ),
                        files=await self._get_files(
                            interaction.guild_id,
                            script_params
                        ),
                        ephemeral=True
                    )
            except Exception as e:
                logger.exception("Any error in script search process")
                err_list.append(e)

        if err_list:
            await interaction.followup.send(  # type: ignore
                "Ошибки в ходе поиска скриптов:\n" + "\n".join(str(e) for e in err_list),
                ephemeral=True
            )

    @staticmethod
    async def _get_files(guild_id: int, script_params: dict[str, Any]):
        files = []

        code_name = f"{guild_id}.{script_params['name']}"
        files.append(
            discord.File(
                fp=BytesIO(
                    script_params["content"]
                    .encode("utf-8")
                ),
                filename=f"{code_name}.content.txt"
            )
        )

        eng_cache = script_params['eng_cache']
        if eng_cache:
            lang = eng_cache['lang']
            files.append(
                discord.File(
                    fp=BytesIO(
                        eng_cache["compiled_code"]
                        .encode("utf-8")
                    ),
                    filename=f"{code_name}.compiled.{lang}"
                )
            )
            files.append(
                discord.File(
                    fp=BytesIO(
                        pformat(eng_cache["env"])
                        .encode("utf-8")
                    ),
                    filename=f"{code_name}.env.{lang}"
                )
            )

        return files

    @staticmethod
    async def _get_script_params(
            db_script: GuardDatabase.script, eng_script: Optional[scripts.BaseScript]
    ) -> dict[str, Any]:
        return {
            "id": db_script.id,
            "name": db_script.name,
            "type": db_script.type,

            "additions": db_script.additions,
            "content": db_script.content,
            "is_active": db_script.is_active,
            "timestamp": db_script.timestamp,

            "eng_cache": {
                "name": eng_script.name,
                "filename": eng_script.filename,
                "lang": eng_script.lang,
                "is_lib": eng_script.is_lib,

                "compiled_code": eng_script.compiled_code,
                "env": {
                    name: value
                    for name, value in eng_script.code_env.items()
                    if not name.startswith("_")
                }
            } if eng_script else {}
        }

    @staticmethod
    async def _get_embed(script_params: dict[str, Any]) -> discord.Embed:
        eng_cache: dict[str, Any] = script_params['eng_cache']

        embed = discord.Embed(
            title=f"{script_params['name']} - script data",
            color=discord.Color.green() if script_params["is_active"] else discord.Color.red(),
            timestamp=datetime.datetime.fromtimestamp(script_params["timestamp"])
        ).add_field(
            name="Identification",
            value=f"id: {script_params['id']}\n"
                  f"name: {script_params['name']}\n"
                  f"filename: {eng_cache.get('filename')}",
            inline=False
        ).add_field(
            name="Status",
            value=f"loaded: {bool(eng_cache)}\n"
                  f"active: {script_params['is_active']}",
            inline=False
        ).add_field(
            name="Type",
            value=f"raw: {script_params['type']}\n"
                  f"lang: {eng_cache.get('lang')}\n"
                  f"is_lib: {eng_cache.get('is_lib')}",
            inline=False
        )

        embed.set_footer(
            text=f"id: {script_params['id']} is_active: {script_params['is_active']}",
            icon_url=
            "https://images.icon-icons.com/2699/PNG/512/python_logo_icon_168886.png"
            if "py" in script_params["type"] else
            "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Lua-Logo.svg/2048px-Lua-Logo.svg.png"
            if "lua" in script_params["type"] else
            None
        )

        return embed


class ScriptView(ui.View):
    def __init__(self, cog: ScriptCog, user: discord.User):
        super().__init__(timeout=None)
        self.cog: ScriptCog = cog
        self._update_buttons(user)

    @ui.button(label="Turn exec mode", style=discord.ButtonStyle.secondary, custom_id="script:toggle_exec")
    async def turn_exec_mode(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use script:toggle_exec")

        await self.cog.turn_exec_mode(interaction)
        self._update_buttons(interaction.user)
        await interaction.response.edit_message(view=self)  # type: ignore

    def _update_buttons(self, user: discord.User):
        session = self.cog.manager.get_seance(user)
        self.turn_exec_mode.label = "⏹️ Остановить" if session else "▶️ Запустить"
        self.turn_exec_mode.style = discord.ButtonStyle.red if session else discord.ButtonStyle.green

    @ui.button(label="♻️ Обновить скрипты", style=discord.ButtonStyle.secondary, custom_id="script:update")
    async def update_scripts(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use script:update")

        await interaction.response.send_modal(  # type: ignore
            UpdateScriptsModal(self.cog)
        )

    @ui.button(label="⚡ Выполнить скрипт", style=discord.ButtonStyle.blurple, custom_id="script:exec")
    async def exec_script(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use script:exec")

        await interaction.response.send_modal(  # type: ignore
            ExecuteScriptModal(self.cog)
        )

    @ui.button(label="🚀 on guild", style=discord.ButtonStyle.primary, custom_id="hub:bot_on_guild")
    @app_commands.guild_only
    async def bot_on_guild(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()  # type: ignore
        await self.cog.engine.guild_on_ready(interaction.guild)
        await interaction.followup.send("✅ Success", ephemeral=True)  # type: ignore


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
        default="True",
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

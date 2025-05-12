import datetime
from pprint import pformat
import json

import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from bot.cogs.script_engine import PythonScript
from bot.bot import GuardBot


class ExecutorSeance:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.env: dict = {}
        self.clear_env()

        self.is_executing = True

    def expand_env(self, **context) -> dict:
        self.env.update(**context)
        return self.env

    def clear_env(self) -> None:
        self.env = {
            "logger": logger,
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

    async def execute(self, code, **context) -> any:
        script = PythonScript.compile(code, self.bot.script_eng)
        try:
            script.code_env.update(**self.env)
            ret = await script.execute(context)
            self.expand_env(**script.code_env)
            self.env["__std_send_response_message__"] = ""
            return ret
        except Exception as e:
            return e
        except RuntimeWarning as e:
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


class BotToolCog(commands.Cog):
    def __init__(self, bot):
        self.bot: GuardBot = bot

        self.manager = ExecutorManager(bot)

    @app_commands.command(name="update_scripts")
    @GuardBot.error_handler
    async def update_scripts(
            self, interaction: discord.Interaction,
            from_db: bool = False
    ):
        checked = await self.bot.check_botdev(interaction)
        if not checked: return

        try:
            logger.debug("Scripts reloading")
            if from_db:
                error_list = await self.bot.script_eng.load_scripts_from_db()
            else:
                error_list = await self.bot.script_eng.load_scripts_from_dir()

            if not error_list:
                await interaction.response.send_message(  # type: ignore
                    "✅ Success"
                )
            else:
                error_messages = ""
                for e, description in error_list:
                    error_messages += "\n" + description

                await interaction.response.send_message(  # type: ignore
                    "⚠️ Any error(s):" + error_messages
                )
        except Exception as e:
            await interaction.response.send_message(  # type: ignore
                f"⚠️ Unexpected error: {e}"
            )
            raise

    @app_commands.command(name="close_bot")
    @GuardBot.error_handler
    async def close_bot(self, interaction: discord.Interaction):
        checked = await self.bot.check_botdev(interaction)
        if not checked: return

        await interaction.channel.send(
            "💤 Try to stop bot working"
        )
        await self.bot.close()

        try:
            await interaction.response.send_message(  # type: ignore
                "⚠️ Command did`nt stop bot working",
                ephemeral=True
            )
        except:
            pass

    @app_commands.command(name="exec_mode")
    @GuardBot.error_handler
    async def exec_mode(self, interaction: discord.Interaction, status: bool):
        checked = await self.bot.check_botdev(interaction)
        if not checked: return

        if self.manager.get_seance(interaction.user): self.manager.delete_seance(interaction.user)

        if status:
            self.manager.create_seance(interaction.user)
            await interaction.response.send_message(  # type: ignore
                "▶️ Execution - on"
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⏹️ Execution - off"
            )

    @app_commands.command(name="exec_mode_status")
    @GuardBot.error_handler
    async def exec_mode_status(self, interaction: discord.Interaction):
        checked = await self.bot.check_botdev(interaction)
        if not checked: return

        if self.manager.get_seance(interaction.user):
            await interaction.response.send_message(  # type: ignore
                "▶️ Now execution - on"
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⏹️ Now execution - off"
            )

    @app_commands.command(name="reload_cogs")
    @GuardBot.error_handler
    async def reload_cogs(self, interaction: discord.Interaction):
        checked = await self.bot.check_botdev(interaction)
        if not checked: return

        await interaction.response.send_message(  # type: ignore
            "🔁 Cogs reloading started"
        )

        await self.bot.re_load_cogs()

    @app_commands.command(name="exec_script")
    @GuardBot.error_handler
    async def exec_script(
            self, interaction: discord.Interaction,
            script_name: str,
            from_db: bool = False,
            kwargs: str = ""
    ):
        try:
            ret = await self.bot.script_eng.execute(
                script_name, interaction.guild_id if from_db else None,
                interaction=interaction,
                **json.loads('{' + kwargs + '}')
            )
            await interaction.response.send_message(  # type: ignore
                "Result:\n"
                "```\n"
                f"{pformat(ret)}"
                "```\n"
            )
        except Exception as e:
            logger.exception("Error in script execution command")
            await interaction.response.send_message(  # type: ignore
                f"Критичная ошибка при выполнении: {e}"
            )
        except RuntimeWarning as e:
            logger.exception("RuntimeWarning in script execution command")
            await interaction.response.send_message(  # type: ignore
                f"Ошибка при выполнении: {e}"
            )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if seance := self.manager.get_seance(msg.author):
            content = msg.content
            if content.startswith("```python"):
                code = content
                code = code.replace("```python", "")
                code = code.replace("```", "")

                try:
                    from pprint import pformat

                    seance.expand_env(
                        send=msg.channel.send
                    )
                    result = await seance.execute(
                        code,
                        msg=msg
                    )

                    await msg.channel.send(
                        (
                            "Error:\n"
                            if isinstance(result, Exception) else
                            "Result:\n"
                        ) +
                        "```python\n"
                        f"{pformat(result)}\n"
                        "```"
                    )
                except Exception as e:
                    logger.exception("Error in script")

                    await msg.channel.send(
                        "Error:\n" + str(e)
                    )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ TestCog loading")
    await bot.add_cog(BotToolCog(bot))

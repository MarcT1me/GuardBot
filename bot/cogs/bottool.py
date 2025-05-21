import asyncio
import datetime
from sys import exit as sys_exit

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from bot.bot import GuardBot


class BotToolCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

    @app_commands.command(name="restart_bot")
    @GuardBot.error_handler()
    @app_commands.describe(
        time="Время в секундах до перезагрузки",
        interval="Время в секундах между выводами"
    )
    @GuardBot.error_handler()
    async def restart_bot(self, interaction: discord.Interaction, time: int = 0, interval: int = 60):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        await interaction.response.defer()  # type: ignore

        if time > 0:
            await self._wait_any(
                interaction,
                wait_time=time, interval_size=interval,
                plan_message="Запланирован рестарт через `{remaining}`.\n"
                             "ЭТО ДЕЙСТВИЕ НЕВОЗМОЖНО ОТМЕНИТЬ!",
            )

        await self._stop_bot(interaction)  # type: ignore
        GuardBot.is_restart = True

    @app_commands.command(name="close_bot")
    @app_commands.describe(
        time="Время в секундах до выключения",
        interval="Время в секундах между выводами"
    )
    @GuardBot.error_handler()
    async def close_bot(self, interaction: discord.Interaction, time: int = 0, interval: int = 60):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        await interaction.response.defer()  # type: ignore

        if time > 0:
            await self._wait_any(
                interaction,
                wait_time=time, interval_size=interval,
                plan_message="Запланировано завершение работы через {wait_time}.\n"
                             "ЭТО ДЕЙСТВИЕ НЕВОЗМОЖНО ОТМЕНИТЬ!",
            )

        await self._stop_bot(interaction)
        sys_exit(0)

    @staticmethod
    async def _wait_any(
            interaction: discord.Interaction,
            wait_time: int,
            interval_size: int,
            plan_message: str
    ):
        message = await interaction.followup.send(
            plan_message.format(remaining=datetime.timedelta(seconds=wait_time))
        )

        for sec in range(0, wait_time, interval_size):
            await asyncio.sleep(interval_size)
            remaining = wait_time - sec - interval_size
            await message.edit(
                content=plan_message.format(remaining=datetime.timedelta(seconds=remaining))
            )

    async def _stop_bot(self, interaction: discord.Interaction):
        await interaction.followup.send(
            "💤 Trying to stop bot working"
        )
        await self.bot.close()

        try:
            await interaction.followup.send("⚠️ Command did`nt stop bot working")
        except:
            pass

    @app_commands.command(name="reload_cogs")
    @GuardBot.error_handler()
    async def reload_cogs(self, interaction: discord.Interaction):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        await interaction.response.send_message(  # type: ignore
            "🔁 Cogs reloading started"
        )

        await self.bot.reload_cogs()


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ BotToolCog loading")
    await bot.add_cog(BotToolCog(bot))

import asyncio
import datetime
from sys import exit as sys_exit

import discord
from discord import ui
from discord.ext import commands
from loguru import logger

from bot.bot import GuardBot


class BotToolCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

    @GuardBot.error_handler(is_defer=True)
    async def restart_bot(self, interaction: discord.Interaction, time: int = 0, interval: int = 60):
        if time > 0:
            await self._wait_any(
                interaction,
                wait_time=time, interval_size=interval,
                plan_message="Запланирован рестарт через `{remaining}`.\n"
                             "ЭТО ДЕЙСТВИЕ НЕВОЗМОЖНО ОТМЕНИТЬ!",
            )

        await self._stop_bot(interaction)  # type: ignore
        GuardBot.is_restart = True

    @GuardBot.error_handler(is_defer=True)
    async def close_bot(self, interaction: discord.Interaction, time: int = 0, interval: int = 60):
        if time > 0:
            await self._wait_any(
                interaction,
                wait_time=time, interval_size=interval,
                plan_message="Запланировано завершение работы через {remaining}.\n"
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
            "💤 bot shutdown proceed started",
            ephemeral=True
        )
        await self.bot.close()

        try:
            await interaction.followup.send("⚠️ Command did`nt stop bot working")
        except:
            pass

    @GuardBot.error_handler(is_defer=True)
    async def reload_cogs(self, interaction: discord.Interaction, cog_list: str = None):
        if cog_list:
            cog_names = [cog + "Cog" for cog in cog_list.split("\\")]
        else:
            cog_names = None

        await interaction.followup.send(  # type: ignore
            "🔁 Cogs reloading started",
            ephemeral=True
        )

        await self.bot.reload_cogs(cog_names)

        await interaction.followup.send(  # type: ignore
            "✅ Cogs reloaded",
            ephemeral=True
        )

        await self.bot.tree.sync()

        await interaction.followup.send(  # type: ignore
            "✅ Cogs synced with tree",
            ephemeral=True
        )


class BotToolView(ui.View):
    def __init__(self, cog: BotToolCog):
        super().__init__(timeout=None)
        self.cog: BotToolCog = cog

    @ui.button(label="🔄 Рестарт бота", style=discord.ButtonStyle.danger)
    async def restart(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_modal(  # type: ignore
            RestartModal(self.cog)
        )

    @ui.button(label="⏹️ Остановка бота", style=discord.ButtonStyle.danger)
    async def shutdown(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_modal(  # type: ignore
            ShutdownModal(self.cog)
        )

    @ui.button(label="⚙️ Перезагрузка Cogs", style=discord.ButtonStyle.danger)
    async def reload_cogs(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_modal(  # type: ignore
            ReloadCogsModal(self.cog)
        )


class RestartModal(ui.Modal, title="Настройка рестарта"):
    time = ui.TextInput(
        label="Задержка (секунды)",
        placeholder="0 для немедленного",
        required=False
    )
    interval = ui.TextInput(
        label="Интервал оповещений",
        placeholder="По умолчанию 60",
        required=False
    )

    def __init__(self, bot_tools: BotToolCog):
        super().__init__()
        self.bot_tools: BotToolCog = bot_tools

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # type: ignore

        time = int(self.time.value) if self.time.value else 0
        interval = int(self.interval.value) if self.interval.value else 600

        await self.bot_tools.restart_bot(interaction, time, interval)


class ShutdownModal(ui.Modal, title="Настройка выключения"):
    time = ui.TextInput(
        label="Задержка (секунды)",
        placeholder="0 для немедленного",
        required=False
    )
    interval = ui.TextInput(
        label="Интервал оповещений",
        placeholder="По умолчанию 60",
        required=False
    )

    def __init__(self, bot_tools: BotToolCog):
        super().__init__()
        self.bot_tools: BotToolCog = bot_tools

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # type: ignore

        time = int(self.time.value) if self.time.value else 0
        interval = int(self.interval.value) if self.interval.value else 600

        await self.bot_tools.close_bot(interaction, time, interval)


class ReloadCogsModal(ui.Modal, title="Перезагрузка Cogs"):
    cogs_list = ui.TextInput(
        label="список Cogs (разделитель \\)",
        placeholder="например: Event\\Fun",
        required=False
    )

    def __init__(self, bot_tools: BotToolCog):
        super().__init__()
        self.bot_tools: BotToolCog = bot_tools

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # type: ignore

        value = self.cogs_list.value
        await self.bot_tools.reload_cogs(interaction, value if value else None)


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ BotToolCog loading")
    await bot.add_cog(
        BotToolCog(bot)
    )

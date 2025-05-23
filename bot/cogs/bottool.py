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
    async def reload_cogs(self, interaction: discord.Interaction, cog_list: list[str] = None):
        await interaction.followup.send(  # type: ignore
            "🔁 Cogs reloading started",
            ephemeral=True
        )

        await self.bot.reload_cogs(cog_list)

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
        logger.warning(f"{interaction.user.name} use restart")
        await interaction.response.send_modal(  # type: ignore
            RestartModal(self.cog)
        )

    @ui.button(label="⏹️ Остановка бота", style=discord.ButtonStyle.danger)
    async def shutdown(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use shutdown")
        await interaction.response.send_modal(  # type: ignore
            ShutdownModal(self.cog)
        )

    @ui.button(label="⚙️ Перезагрузка Cogs", style=discord.ButtonStyle.danger)
    async def reload_cogs(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use reload_cogs")
        view = ReloadCogsView(self.cog)
        await interaction.response.send_message(  # type: ignore
            "Выберите запчасти для перезагрузки",
            view=view,
            ephemeral=True
        )


class ReloadCogsView(ui.View):
    def __init__(self, bot_tools: BotToolCog):
        super().__init__()
        self.bot_tools: BotToolCog = bot_tools

        cogs_names = self.bot_tools.bot.cogs.keys()

        self.select = ui.Select(
            placeholder="выберите запчасти к перезагрузке",
            options=[
                *[
                    discord.SelectOption(label=cog_name, value=cog_name)
                    for cog_name in cogs_names
                ],
                discord.SelectOption(label="All", value="All")
            ],
            max_values=len(cogs_names),
            custom_id="log_list:select_one"
        )
        self.select.callback = self.select_one
        self.add_item(self.select)

    async def select_one(self, interaction: discord.Interaction):
        logger.warning(f"{interaction.user.name} use log_list:select_one")
        await interaction.response.defer(ephemeral=True)  # type: ignore

        selected_cogs = self.select.values
        await self.bot_tools.reload_cogs(
            interaction,
            selected_cogs
            if selected_cogs and "All" not in selected_cogs else
            None
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


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ BotToolCog loading")
    await bot.add_cog(
        BotToolCog(bot)
    )

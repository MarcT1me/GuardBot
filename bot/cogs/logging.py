from datetime import datetime
import os

import discord
from discord import app_commands, ui
from discord.ext import commands
from loguru import logger

from bot import GuardBot, GuardLogger


class LoggingCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.manager: GuardLogger = bot.logger
        self.bot.add_view(LogView(self.manager))

    @app_commands.command(
        name="log_hub",
        description="Управление системой логирования"
    )
    async def log_hub(self, interaction: discord.Interaction):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        view = LogView(self.manager)

        return await interaction.response.send_message(  # type: ignore
            "**Панель управления логами**\n"
            "Выберите действие:",
            view=view,
            ephemeral=True
        )


class LogView(ui.View):
    def __init__(self, manager: GuardLogger):
        super().__init__(timeout=None)
        self.manager: GuardLogger = manager
        self._update_buttons()

    def _update_buttons(self):
        self.turn_logging.label = (
            "⏹️ Остановить"
            if self.manager.logging_active
            else "▶️ Запустить"
        )
        self.turn_logging.style = (
            discord.ButtonStyle.red
            if self.manager.logging_active
            else discord.ButtonStyle.green
        )

    @ui.button(label="▶️ Запустить", style=discord.ButtonStyle.green, custom_id="log:toggle")
    async def turn_logging(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use log:toggle")

        if self.manager.logging_active:
            self.manager.stop()
        else:
            self.manager.start()

        # Обновляем сообщение с новым состоянием
        self._update_buttons()
        await interaction.response.edit_message(view=self)  # type: ignore

    @ui.button(label="📂 Получить список логов", style=discord.ButtonStyle.blurple, custom_id="log:get_list")
    async def get_list(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use log:get_list")
        await interaction.response.defer(ephemeral=True)  # type: ignore

        log_list: list[str] = sorted(os.listdir(self.manager.log_dir))

        filenames: list[str] = [
            f"> {i + 1}) **{filename}**"
            for i, filename in enumerate(log_list)
            if filename.endswith(".log")
        ]

        view = LogFileListView(self.manager, log_list[:25])

        await interaction.followup.send(  # type: ignore
            f"📁 Нашёл файлов: {len(filenames)}\n" +
            "\n".join(filenames),
            view=view,
            ephemeral=True
        )


class LogFileListView(ui.View):
    def __init__(self, manager: GuardLogger, log_list: list[str]):
        super().__init__()
        self.manager: GuardLogger = manager

        self.select = ui.Select(
            placeholder="📂 Получить лог-файл",
            options=[
                discord.SelectOption(label=filename, value=filename)
                for filename in log_list
            ],
            max_values=len(log_list),
            custom_id="log_list:select_one"
        )
        self.select.callback = self.select_one
        self.add_item(self.select)

    async def select_one(self, interaction: discord.Interaction):
        logger.warning(f"{interaction.user.name} use log_list:select_one")
        await interaction.response.defer(ephemeral=True)  # type: ignore

        log_file = self.select.values[0]
        target_time = datetime.strptime(
            log_file.replace(".log", ""), "%d-%m-%Y"
        )

        log_file = discord.File(os.path.join(self.manager.log_dir, log_file), log_file)

        await interaction.followup.send(
            f"📁 Лог от `{target_time}`:",
            ephemeral=True,
            file=log_file
        )

    @ui.button(label="Обновить список", style=discord.ButtonStyle.secondary)
    async def update_all(self, interaction: discord.Interaction, _: ui.Button):
        log_list = sorted(os.listdir(self.manager.log_dir))
        filenames: list[str] = [
            f"> {i + 1}) **{filename}**"
            for i, filename in enumerate(log_list)
            if filename.endswith(".log")
        ]

        self._update_select(log_list[:25])
        await interaction.response.edit_message(  # type: ignore
            content=f"📁 Нашёл файлов: {len(filenames)}\n" +
                    "\n".join(filenames),
            view=self
        )

    def _update_select(self, log_list: list[str]):
        self.select.options = [
            discord.SelectOption(label=filename, value=filename)
            for filename in log_list
        ]
        self.select.max_values = len(log_list)


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ LoggingCog loading")
    await bot.add_cog(
        LoggingCog(
            bot
        )
    )

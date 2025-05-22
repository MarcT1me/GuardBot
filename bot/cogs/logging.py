import os
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import ui, app_commands
from discord.ext import commands

from loguru import logger

from bot import GuardBot


class GuardLogger:
    def __init__(self, *, log_dir: str = "logs", logging_active: bool = False):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.logging_active: bool = logging_active
        self.current_logger: Optional[int] = None

    def start(self):
        self.logging_active = True

        file_sink = str(self.log_dir) + "/{time:YYYYMMDD_HHmmss}.log"
        rotation = 2000000
        retention = timedelta(hours=1)

        self.current_logger = logger.start(
            sink=file_sink,
            encoding="utf-8",
            rotation=rotation,
            retention=retention,
        )

        logger.info("Логирование активировано")

    def stop(self):
        self.logging_active = False

        logger.info("Логирование остановлено")
        if self.current_logger:
            logger.remove(self.current_logger)


class LogGetterModal(ui.Modal):
    def __init__(self, manager: GuardLogger):
        super().__init__(title="Поиск логов", timeout=None)
        self.manager: GuardLogger = manager
        self.add_item(
            ui.TextInput(
                label="Время начала (DD-MM-YYYY_HH:MM)",
                placeholder="Пример: 23-10-2023_15:30",
                required=True,
                min_length=16,
                max_length=16
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # type: ignore
        timestamp = self.children[0].value  # type: ignore

        try:
            target_time = datetime.strptime(timestamp, "%d-%m-%Y_%H:%M")
            found_files = []

            # Ищем все логи начиная с указанного времени
            for filename in sorted(os.listdir(self.manager.log_dir)):
                if not filename.endswith(".log"):
                    continue
                try:
                    file_time = datetime.strptime(filename[:13], "%Y%m%d_%H%M")
                    if file_time >= target_time:
                        found_files.append(filename)
                except ValueError:
                    continue

            if not found_files:
                return await interaction.followup.send("🔍 Логов не найдено", ephemeral=True)

            # Отправляем первый подходящий файл
            file_path = os.path.join(self.manager.log_dir, found_files[0])
            log_file = discord.File(file_path, str(found_files[0][:15]) + ".log")

            await interaction.followup.send(
                f"📁 Лог от `{target_time}`:",
                ephemeral=True,
                file=log_file
            )

        except Exception as e:
            await interaction.followup.send(f"🚨 Ошибка: {str(e)}", ephemeral=True)


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
        logger.warning(f"{interaction.user.name} use turn_logging")

        if self.manager.logging_active:
            self.manager.stop()
        else:
            self.manager.start()

        # Обновляем сообщение с новым состоянием
        self._update_buttons()
        await interaction.response.edit_message(view=self)  # type: ignore

    @ui.button(label="📂 Получить логи", style=discord.ButtonStyle.blurple, custom_id="log:get")
    async def get_logs(self, interaction: discord.Interaction, _: ui.Button):
        logger.warning(f"{interaction.user.name} use get_logs")

        modal = LogGetterModal(self.manager)
        await interaction.response.send_modal(modal)  # type: ignore


class LoggingCog(commands.Cog):
    def __init__(self, bot: GuardBot, manager: GuardLogger):
        self.bot: GuardBot = bot
        self.manager: GuardLogger = manager
        self.bot.add_view(LogView(self.manager))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async with self.bot.wait_for_cog_loading(1):
            pass
            if self.manager.logging_active:
                self.manager.start()

    @app_commands.command(
        name="logs",
        description="Управление системой логирования"
    )
    async def logs_command(self, interaction: discord.Interaction):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message(  # type: ignore
                "GET OF FUCK OUT!!! 🤬🤬🤬"
            )

        view = LogView(self.manager)

        await interaction.response.send_message(  # type: ignore
            "**Панель управления логами**\n"
            "Выберите действие:",
            view=view,
            ephemeral=True
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ LoggingCog loading")
    await bot.add_cog(
        LoggingCog(
            bot,
            GuardLogger(logging_active=True)
        )
    )

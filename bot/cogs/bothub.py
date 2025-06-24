import discord
from discord import app_commands
from discord import ui
from discord.ext import commands
from loguru import logger

from bot.bot import GuardBot
from .bottool import BotToolView
from .test_tools import TestToolsView


class BotHubCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot = bot
        self.bot.add_view(MainHub(bot))

    @app_commands.command(name="botdev_hub", description="Главное меню управления ботом")
    async def botdev_hub(self, interaction: discord.Interaction):
        passed = await self.bot.check_botdev(interaction)
        if not passed:
            return await interaction.response.send_message("GET OF FUCK OUT!!! 🤬🤬🤬", ephemeral=True)  # type: ignore

        view = MainHub(self.bot)
        embed = discord.Embed(
            title="🔧 Панель управления ботом",
            description="Выберите категорию управления:"
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)  # type: ignore


class MainHub(ui.View):
    def __init__(self, bot: GuardBot):
        super().__init__(timeout=None)
        self.bot: GuardBot = bot

    @ui.button(label="🛠️ Bot Tools", style=discord.ButtonStyle.primary, custom_id="hub:bot_tools")
    async def bot_tools(self, interaction: discord.Interaction, _: ui.Button):
        cog = self.bot.get_cog("BotToolCog")
        view = BotToolView(cog)

        embed = discord.Embed(
            title="Управление ботом",
            description="Основные команды для управления работой бота"
        ).add_field(
            name="Рестарт бота",
            value="`/restart_bot [time] [interval]`\n"
                  "Плавный перезапуск бота"
        ).add_field(
            name="Остановка бота",
            value="`/close_bot [time] [interval]`\n"
                  "Полное выключение бота"
        ).add_field(
            name="Перезагрузка Cogs",
            value="`/reload_extensions [extensions_list]`\n"
                  "Полная перезагрузка расширений бота"
        )

        await interaction.response.send_message(  # type: ignore
            embed=embed,
            view=view,
            ephemeral=True
        )

    @ui.button(label="🧪 Test Commands", style=discord.ButtonStyle.primary, custom_id="hub:bot_tests")
    @app_commands.guild_only
    async def bot_test_commands(self, interaction: discord.Interaction, _: ui.Button):
        cog = self.bot.get_cog("TestToolsCog")
        view = TestToolsView(cog)

        embed = discord.Embed(
            title="Тестовые команды",
            description="Команды для тестирования функционала"
        ).add_field(
            name="Вызов исключения",
            value="`/test_drop_exc`\n"
                  "Генерирует тестовое исключение"
        ).add_field(
            name="HTTP Тест",
            value="`/test_drop_http [force]`\n"
                  "Тест обработки HTTP ошибок"
        )

        await interaction.response.send_message(  # type: ignore
            embed=embed,
            view=view,
            ephemeral=True
        )


async def setup(bot: GuardBot):
    logger.debug("⚙️ BotHubCog loading")
    await bot.add_cog(
        BotHubCog(bot)
    )

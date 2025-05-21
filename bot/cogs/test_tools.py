import discord
from discord import ui
from discord.ext import commands
from loguru import logger

from bot.bot import GuardBot


class TestToolsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @GuardBot.error_handler(is_defer=True)
    @GuardBot.has_permission(administrator=True)
    async def test_drop_exc(self, interaction: discord.Interaction):
        class TestDropException(Exception):
            pass

        await interaction.followup.send(
            f"""Выкидываю `raise TestDropException<Exception>("TEST DROP")`. уровень - ErrorLevel.First""",
            ephemeral=True
        )
        raise TestDropException("TEST DROP")

    @GuardBot.error_handler(is_defer=True)
    @GuardBot.has_permission(administrator=True)
    async def test_drop_http(self, interaction: discord.Interaction, force: bool = False):
        await interaction.followup.send(  # type: ignore
            "Попытка создать канал с длинной 101/100",
            ephemeral=True
        )

        channel = await interaction.guild.create_text_channel(
            "a" * 101,
            reason=GuardBot.normalized_reason(interaction.user, "try create channel with bad name")
        )

        await interaction.followup.send(  # type: ignore
            "❌ Не сработало, очищаю за собой",
            ephemeral=True
        )
        await channel.delete(reason="revert changes")

        channels = []
        if force:
            for i in range(50):
                channel_name = f"force-test-spam-channel-{i}"
                channels.append(
                    await interaction.guild.create_text_channel(
                        channel_name,
                        reason=GuardBot.normalized_reason(interaction.user, channel_name)
                    )
                )

        await interaction.followup.send(  # type: ignore
            "❌ Не сработало, очищаю за собой",
            ephemeral=True
        )
        for channel in channels: await channel.delete(reason="revert changes")


class TestToolsView(ui.View):
    def __init__(self, cog: TestToolsCog):
        super().__init__(timeout=None)
        self.cog: TestToolsCog = cog

    @ui.button(label="🔥 Вызвать ошибку", style=discord.ButtonStyle.secondary)
    async def raise_error(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()  # type: ignore
        await self.cog.test_drop_exc(interaction)
        await interaction.followup.send(
            "Тест завершен",
            ephemeral=True
        )

    @ui.button(label="🌐 HTTP Тест", style=discord.ButtonStyle.secondary)
    async def http_test(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_modal(  # type: ignore
            TestHTTPModel(self.cog)
        )


class TestHTTPModel(ui.Modal, title="Настройка выключения"):
    force = ui.TextInput(
        label="Усиленный режим (доп. действия)",  # Сокращено до 32 символов
        placeholder="True для активации",
        required=False
    )

    def __init__(self, bot_tools: TestToolsCog):
        super().__init__()
        self.test: TestToolsCog = bot_tools

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # type: ignore
        await self.test.test_drop_http(interaction, self.force.value == "True")
        await interaction.followup.send(
            "Тест завершен",
            ephemeral=True
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ TestToolsCog loading")
    await bot.add_cog(
        TestToolsCog(bot)
    )

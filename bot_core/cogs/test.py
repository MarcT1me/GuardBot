import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from bot_core.bot import GuardBot


class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test_drop_exc", description="Выбрасывает ошибку выбранного уровня (1, 2)")
    @GuardBot.error_handler
    @GuardBot.has_permission(administrator=True)
    async def test_drop_exc(self, interaction: discord.Interaction, level: int):
        class TestDropException(Exception):
            pass

        match level:
            case 1:
                await interaction.channel.send(
                    f"""Выкидываю `raise TestDropException<Exception>("TEST DROP")`. уровень - ErrorLevel.First"""
                )
                raise TestDropException("TEST DROP")
            case 2:
                await interaction.channel.send(  # type: ignore
                    f"""Выкидываю `raise TestDropException<Exception>("TEST DROP")`. уровень - ErrorLevel.Second"""
                )
                raise TestDropException("TEST DROP")

    @app_commands.command(name="test_drop_http", description="вызывает ошибку HTTP 400")
    @GuardBot.error_handler
    @GuardBot.has_permission(administrator=True)
    async def test_drop_http(self, interaction: discord.Interaction, force: bool = False):
        channel = await interaction.guild.create_text_channel(
            "a" * 101,
            reason=GuardBot.normalized_reason(interaction.user, "try create channel with bad name")
        )

        await interaction.channel.send(  # type: ignore
            "❌ Не сработало, очищаю за собой"
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

        await interaction.response.send(  # type: ignore
            "❌ Не сработало, очищаю за собой"
        )
        for channel in channels: await channel.delete(reason="revert changes")

        await interaction.response.send(  # type: ignore
            "❌ Не сработало."
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ TestCog loading")
    await bot.add_cog(TestCog(bot))

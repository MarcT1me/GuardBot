import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from loguru import logger

from bot_core.bot import try_execute, GuardBot


class DiscordPermissionError(Exception):
    pass


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def check_role_hierarchy(user: discord.Member | discord.User, role: discord.Role):
        owner_roles = user.roles
        if len(owner_roles) > 1:
            highest_role_level = owner_roles[-1].position
        else:
            highest_role_level = 0

        if role.position > highest_role_level:
            return 0
        elif role.position == highest_role_level:
            return 1
        else:
            return 2

    @app_commands.command(name="add_role", description="Выдаёт участнику роль")
    @app_commands.checks.has_permissions(manage_roles=True)
    @try_execute
    async def add_role(self, interaction: discord.Interaction,
                       member: discord.Member,
                       role: discord.Role,
                       reason: str | None = None
                       ):
        """Добавить роль пользователю"""
        if self.check_role_hierarchy(interaction.user, role):
            await member.add_roles(
                role,
                reason=reason
            )
            await interaction.response.send_message(  # type: ignore
                f"Роль {role.mention} выдана {member.mention}" + ("\nпричина: " + reason if reason else ""),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "❌ У меня не вышло выдать роль! Причина - роль выше вашей.",
                ephemeral=True
            )

    @app_commands.command(name="del_role", description="Убирает у участника роль")
    @app_commands.checks.has_permissions(manage_roles=True)
    @try_execute
    async def del_role(self, interaction: discord.Interaction,
                       member: discord.Member,
                       role: discord.Role,
                       reason: str | None = None
                       ):
        """Убрать роль у пользователя"""
        if self.check_role_hierarchy(interaction.user, role) == 2:
            await member.remove_roles(
                role,
                reason=reason
            )
            await interaction.response.send_message(  # type: ignore
                f"Роль {role.mention} убрана с участника {member.mention}" + ("\nпричина: " + reason if reason else ""),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "❌ У меня не вышло забрать роль! Причина - роль выше вашей.",
                ephemeral=True
            )

    @app_commands.command(name="create_channel", description="Создаёт текстовый канал")
    @app_commands.checks.has_permissions(manage_channels=True)
    @try_execute
    async def create_channel(self, interaction: discord.Interaction, channel_name: str,
                             category: discord.CategoryChannel = None,
                             chanel_type: discord.ChannelType = discord.ChannelType.text,
                             reason: str | None = None
                             ):
        """Создать текстовый канал"""
        guild = interaction.guild
        normalized_name = self.normalize_channel_name(channel_name)

        # Проверяем существование канала с нормализованным именем
        existing = get(guild.channels, name=normalized_name)

        if not existing:
            new_channel = None
            match chanel_type:
                case discord.ChannelType.text:
                    new_channel = await guild.create_text_channel(
                        normalized_name, category=category, reason=reason
                    )
                case discord.ChannelType.voice:
                    new_channel = await guild.create_voice_channel(
                        normalized_name, category=category, reason=reason
                    )
            if new_channel:
                await interaction.response.send_message(  # type: ignore
                    f"✅ Канал {new_channel.mention} создан" + ("\nпричина: " + reason if reason else "")
                )
            else:
                await interaction.response.send_message(  # type: ignore
                    f"❌ Не могу создать канал. Скорее всего не правильный тип канала",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(  # type: ignore
                f"⚠️ Канал с именем `{normalized_name}` уже существует",
                ephemeral=True
            )

    @app_commands.command(name="delete_channel", description="Удаляет текстовый канал")
    @app_commands.checks.has_permissions(manage_channels=True)
    @try_execute
    async def delete_channel(self, interaction: discord.Interaction,
                             channel: discord.TextChannel,
                             reason: str | None = None
                             ):
        """Создать текстовый канал"""
        await channel.delete(reason=reason)
        await interaction.response.send_message(  # type: ignore
            f"✅ Канал {channel.name} удалён"
        )

    @staticmethod
    def normalize_channel_name(name: str) -> str:
        """Нормализация имени канала по правилам Discord"""
        return name.lower().replace(' ', '-').strip()

    @app_commands.command(name="test_drop", description="Создаёт текстовый канал")
    @app_commands.checks.has_permissions(administrator=True)
    @try_execute
    async def test_drop(self, interaction: discord.Interaction, level: int):
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


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ModerationCog loading")
    await bot.add_cog(ModerationCog(bot))

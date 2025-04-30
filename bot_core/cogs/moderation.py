import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from bot_core.bot import try_execute


class RoleAssignmentError(Exception):
    pass


class ModerationCog(commands.Cog):
    """Команды модерации"""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def check_role_permissions(user: discord.Member | discord.User, role: discord.Role):
        owner_roles = user.roles
        if len(owner_roles) > 1:
            highest_role_level = owner_roles[-1].position
        else:
            highest_role_level = 0

        if role.position < highest_role_level:
            return 0
        elif role.position == highest_role_level:
            return 1
        else:
            return 2

    @staticmethod
    async def check_permissions(interaction: discord.Interaction, **perms: bool) -> bool:
        """Кастомная проверка прав пользователя и бота"""
        # Проверка что команда используется на сервере
        if not interaction.guild:
            await interaction.response.send_message("❌ Эта команда работает только на серверах!", ephemeral=True)
            return False

        # Проверка прав пользователя
        user_permissions = interaction.user.guild_permissions
        missing_user = [perm for perm, value in perms.items() if getattr(user_permissions, perm, None) != value]

        if missing_user:
            human_perms = ", ".join([f"`{perm.replace('_', ' ')}`" for perm in missing_user])
            await interaction.response.send_message(
                f"❌ Вам не хватает прав: {human_perms}",
                ephemeral=True
            )
            return False

        # Проверка прав бота
        bot_permissions = interaction.guild.me.guild_permissions
        missing_bot = [perm for perm, value in perms.items() if getattr(bot_permissions, perm, None) != value]

        if missing_bot:
            human_perms = ", ".join([f"`{perm.replace('_', ' ')}`" for perm in missing_bot])
            await interaction.response.send_message(
                f"❌ Мне не хватает прав: {human_perms}",
                ephemeral=True
            )
            return False

        return True

    @app_commands.command(name="add_role", description="Выдаёт участнику роль")
    @app_commands.checks.has_permissions(manage_roles=True)
    @try_execute
    async def add_role(self, interaction: discord.Interaction,
                       member: discord.Member,
                       role: discord.Role,
                       reason: str | None = None
                       ):
        """Добавить роль пользователю"""
        if self.check_role_permissions(interaction.user, role):
            await member.add_roles(
                role,
                reason=reason,
                atomic=True
            )

            await interaction.response.send_message(  # type: ignore
                f"Роль {role.mention} выдана {member.mention}",
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "❌ У меня не вышло выдать роль! Причина - выдаваемая роль выше вышей роли",
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
        if self.check_role_permissions(interaction.user, role) == 2:
            await member.remove_roles(
                role,
                reason=reason,
                atomic=True
            )

            await interaction.response.send_message(  # type: ignore
                f"Роль {role.mention} убрана с участника {member.mention}",
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "❌ У меня не вышло убрать роль! Причина - убираемая роль выше вышей роли",
                ephemeral=True
            )

    @app_commands.command(name="create_channel", description="Создаёт текстовый канал")
    @app_commands.checks.has_permissions(manage_channels=True)
    @try_execute
    async def create_channel(self, interaction: discord.Interaction, channel_name: str):
        """Создать текстовый канал"""
        guild = interaction.guild
        existing = get(guild.channels, name=channel_name)

        if not existing:
            new_channel = await guild.create_text_channel(channel_name)
            await interaction.response.send_message(  # type: ignore
                f"Канал {new_channel.mention} создан"
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⚠️ Такой канал уже существует",
                ephemeral=True
            )

    @app_commands.command(name="test_drop", description="Создаёт текстовый канал")
    @app_commands.checks.has_permissions(administrator=True)
    @try_execute
    async def test_drop(self, interaction: discord.Interaction):
        raise Exception("test exception")


async def setup(bot: commands.Bot):
    print(f"⚙️ ModerationCog loading")
    await bot.add_cog(ModerationCog(bot))

import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from bot_core.bot import GuardBot


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
    @GuardBot.error_handler
    @GuardBot.has_permission(manage_roles=True)
    async def add_role(self, interaction: discord.Interaction,
                       member: discord.Member,
                       role: discord.Role,
                       reason: str | None = None
                       ):
        normalized_reason = GuardBot.normalized_reason(interaction.user, reason)

        """Добавить роль пользователю"""
        if self.check_role_hierarchy(interaction.user, role):
            await member.add_roles(
                role,
                reason=normalized_reason
            )
            await interaction.response.send_message(  # type: ignore
                f"Роль {role.mention} выдана {member.mention}" + (
                    "\nПричина: " + reason if reason else ""
                ),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⚠️ У меня не вышло выдать роль. ||Роль выше вашей||",
                ephemeral=True
            )

    @app_commands.command(name="del_role", description="Убирает у участника роль")
    @GuardBot.error_handler
    @GuardBot.has_permission(manage_roles=True)
    async def del_role(self, interaction: discord.Interaction,
                       member: discord.Member,
                       role: discord.Role,
                       reason: str | None = None
                       ):
        normalized_reason = GuardBot.normalized_reason(interaction.user, reason)

        """Убрать роль у пользователя"""
        if self.check_role_hierarchy(interaction.user, role) == 2:
            await member.remove_roles(
                role,
                reason=normalized_reason
            )
            await interaction.response.send_message(  # type: ignore
                f"Роль {role.mention} убрана с участника {member.mention}" + (
                    "\nПричина: " + reason if reason else ""
                ),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⚠️ У меня не вышло забрать роль. ||Роль выше вашей||",
                ephemeral=True
            )

    @app_commands.command(name="create_channel", description="Создаёт канал указанного типа")
    @GuardBot.error_handler
    @GuardBot.has_permission(manage_channels=True)
    async def create_channel(
            self,
            interaction: discord.Interaction,
            channel_name: str,
            category: discord.CategoryChannel | None = None,
            channel_type: discord.ChannelType = discord.ChannelType.text,
            reason: str | None = None
    ):
        """Создать канал любого типа с расширенными проверками"""
        guild = interaction.guild

        # Нормализация параметров
        normalized_name = self.normalize_channel_name(channel_name)
        normalized_reason = GuardBot.normalized_reason(interaction.user, reason)

        # Проверка для категорий
        if channel_type == discord.ChannelType.category:
            if category:
                return await interaction.response.send_message(  # type: ignore
                    "⚠️ Категории нельзя создавать внутри других категорий!",
                    ephemeral=True
                )
            existing = discord.utils.get(guild.categories, name=normalized_name)
        else:
            # Проверяем во всех каналах категории (если указана)
            existing = discord.utils.find(
                lambda c: c.name == normalized_name and c.category == category,
                guild.channels
            )

        if existing:
            return await interaction.response.send_message(  # type: ignore
                f"⚠️ {'Категория' if channel_type == discord.ChannelType.category else 'Канал'} "
                f"с именем `{normalized_name}` уже существует!",
                ephemeral=True
            )

        # Создание каналов
        create_methods: dict = {
            discord.ChannelType.text: guild.create_text_channel,
            discord.ChannelType.voice: guild.create_voice_channel,
            discord.ChannelType.stage_voice: guild.create_stage_channel,
            discord.ChannelType.forum: guild.create_forum,
            discord.ChannelType.category: guild.create_category
        }

        if channel_type not in create_methods:
            return await interaction.response.send_message(  # type: ignore
                "⚠️ Неподдерживаемый тип канала!",
                ephemeral=True
            )

        # Отдельная логика для категорий
        if channel_type == discord.ChannelType.category:
            new_channel = await create_methods[channel_type](
                name=normalized_name,
                reason=normalized_reason
            )
        else:
            new_channel = await create_methods[channel_type](
                name=normalized_name,
                category=category,
                reason=normalized_reason
            )

        # Формирование ответа
        response = (
            f"✅ {'Категория' if channel_type == discord.ChannelType.category else 'Канал'} "
            f"{new_channel.mention if hasattr(new_channel, 'mention') else f'`{normalized_name}`'} создан"
        )
        if reason:
            response += f"\nПричина: {reason}"

        await interaction.response.send_message(  # type: ignore
            response
        )

    @staticmethod
    def normalize_channel_name(name: str) -> str:
        """Приведение имени канала к правильному формату"""
        return name.strip().lower().replace(' ', '-')[:100]

    @app_commands.command(name="delete_channel", description="Удаляет текстовый канал")
    @GuardBot.error_handler
    @GuardBot.has_permission(manage_channels=True)
    async def delete_channel(self, interaction: discord.Interaction,
                             channel: discord.TextChannel,
                             reason: str | None = None
                             ):

        """Создать текстовый канал"""
        await channel.delete(
            reason=GuardBot.normalized_reason(interaction.user, reason)
        )
        await interaction.response.send_message(  # type: ignore
            f"✅ Канал `{channel.name}` удалён" + ("\nпричина: " + reason if reason else "")
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ModerationCog loading")
    await bot.add_cog(ModerationCog(bot))

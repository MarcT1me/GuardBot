from enum import Enum
from typing import Callable

import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger

from bot.bot import GuardBot


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _check_role_hierarchy(user: discord.Member | discord.User, role: discord.Role) -> int:
        """ Проверка на иерархию ролей.
         Возвращает значения от 0 до 2
         0 - если роль выше
         1 - если роль равна
         2 - если роль ниже
         так мы ранжируем роли, можно определить равны ли они, выше или ниже она, выбранные варианты позволяют легко
         определить как иерархию роли и если нужно проверить её, хотя можно и без проверок"""

        owner_roles = user.roles
        highest_role_level = owner_roles.pop().position if len(owner_roles) > 1 else 0

        if role.position > highest_role_level:
            return 0
        elif role.position == highest_role_level:
            return 1
        return 2

    @staticmethod
    def _normalize_channel_name(name: str) -> str:
        """Приведение имени канала к правильному формату"""
        return name.strip().lower().replace(' ', '-')[:100]

    @app_commands.command(name="add_role", description="Выдаёт участнику роль")
    @GuardBot.error_handler()
    @GuardBot.has_permission(manage_roles=True)
    async def add_role(
            self, interaction: discord.Interaction,
            member: discord.Member,
            role: discord.Role,
            reason: str | None = None
    ):
        """Добавить роль пользователю"""
        normalized_reason = GuardBot.normalized_reason(interaction.user, reason)

        if self._check_role_hierarchy(
                interaction.user, role
        ):  # проверяю на то, чтобы роль просто не была выше
            await member.add_roles(
                role,
                reason=normalized_reason
            )
            await interaction.response.send_message(  # type: ignore
                GuardBot.normalize_response_reason(f"Роль {role.mention} выдана {member.mention}", reason),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⚠️ У меня не вышло выдать роль. ||Роль выше вашей||",
                ephemeral=True
            )

    @app_commands.command(name="del_role", description="Убирает у участника роль")
    @GuardBot.error_handler()
    @GuardBot.has_permission(manage_roles=True)
    async def del_role(
            self, interaction: discord.Interaction,
            member: discord.Member,
            role: discord.Role,
            reason: str | None = None
    ):
        """Убрать роль у пользователя"""
        normalized_reason = GuardBot.normalized_reason(interaction.user, reason)

        if self._check_role_hierarchy(
                interaction.user, role
        ) == 2:  # в этом случае обязательно проверить чтобы роль была ниже
            await member.remove_roles(
                role,
                reason=normalized_reason
            )
            await interaction.response.send_message(  # type: ignore
                GuardBot.normalize_response_reason(f"Роль {role.mention} убрана с участника {member.mention}", reason),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False)
            )
        else:
            await interaction.response.send_message(  # type: ignore
                "⚠️ У меня не вышло забрать роль. ||Роль выше вашей||",
                ephemeral=True
            )

    @app_commands.command(name="create_channel", description="Создаёт канал указанного типа")
    @GuardBot.error_handler()
    @GuardBot.has_permission(manage_channels=True)
    async def create_channel(
            self, interaction: discord.Interaction,
            channel_name: str,
            category: discord.CategoryChannel | None = None,
            channel_type: discord.ChannelType = discord.ChannelType.text,
            reason: str | None = None
    ):
        """Создать канал любого типа с расширенными проверками"""
        guild = interaction.guild  # узнаю сервер
        normalized_name = self._normalize_channel_name(channel_name)
        normalized_reason = GuardBot.normalized_reason(interaction.user, reason)

        # ищу все каналы с такой-же в категории
        existing = discord.utils.find(
            lambda c: c.name == normalized_name and c.category == category,
            guild.channels
        )

        if existing:
            # ну если такая уже есть, низя
            return await interaction.response.send_message(  # type: ignore
                f"⚠️ {'Категория' if channel_type == discord.ChannelType.category else 'Канал'} "
                f"с именем `{normalized_name}` уже существует!",
                ephemeral=True
            )

        # списки каналов которые можно создать
        create_methods: dict[Enum, Callable] = {
            discord.ChannelType.text: guild.create_text_channel,
            discord.ChannelType.voice: guild.create_voice_channel,
            discord.ChannelType.stage_voice: guild.create_stage_channel,
            discord.ChannelType.forum: guild.create_forum,
        }

        if channel_type not in create_methods:
            # если не правильно указан тип говорю об этом
            return await interaction.response.send_message(  # type: ignore
                "⚠️ Неподдерживаемый тип канала!\n"
                "можно создавать только каналы типов:\n"
                f"{str(
                    [channel_type.name for channel_type in create_methods.keys()]
                )[1:-1]}",  # выдаю имена всех типов которые можно использовать, убирая скобки
                ephemeral=True
            )

        new_channel = await create_methods[channel_type](
            name=normalized_name,
            category=category,
            reason=normalized_reason
        )

        # Формирование ответа
        await interaction.response.send_message(  # type: ignore
            GuardBot.normalize_response_reason(f"✅ Канал {new_channel.mention} создан", reason)
        )

    @app_commands.command(name="delete_channel", description="Удаляет текстовый канал")
    @GuardBot.error_handler()
    @GuardBot.has_permission(manage_channels=True)
    async def delete_channel(
            self, interaction: discord.Interaction,
            channel: discord.TextChannel,
            reason: str | None = None
    ):
        """Создать текстовый канал"""
        await channel.delete(
            reason=GuardBot.normalized_reason(interaction.user, reason)
        )
        await interaction.response.send_message(  # type: ignore
            GuardBot.normalize_response_reason(f"✅ Канал `{channel.name}` удалён", reason)
        )

    @app_commands.command(name="kick", description="Выгоняет участника")
    @GuardBot.error_handler()
    @GuardBot.has_permission(administration=True)
    async def kick(
            self, interaction: discord.Interaction,
            member: discord.Member,
            reason: str | None = None
    ):
        """Создать текстовый канал"""
        await member.guild.kick(
            member,
            reason=GuardBot.normalized_reason(interaction.user, reason)
        )
        await interaction.response.send_message(  # type: ignore
            GuardBot.normalize_response_reason(
                f"Участник {member.name} изгнан с сервера",
                reason
            )
        )


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ ModerationCog loading")
    await bot.add_cog(ModerationCog(bot))

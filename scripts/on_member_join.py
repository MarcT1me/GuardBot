import discord

import bot
from bot.database.models import Server, Template, UserRole


async def main(bot: bot.GuardBot, *, member: discord.Member):
    system_channel = member.guild.system_channel
    if system_channel:
        await system_channel.send(f"➕ Добро пожаловать, {member.mention}!")


    server = await Server.get_or_none(guild_id=member.guild.id)
    if not server:
        return

    template = await Template.filter(server=server).first()

    roles = await UserRole.filter(server=server)

    roles = await UserRole.filter(server=server)
    role_descriptions = "\n".join(
        f"{discord.Object(role.emoji_id)} - {role.description}"
        for role in roles if role.emoji_id
    )

    await member.send(
        f"**Добро пожаловать на {member.guild.name}!**\n"
        f"{template.content if template else 'Выберите роли:'}\n"
        f"{role_descriptions}"
    )

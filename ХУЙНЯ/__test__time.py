import datetime
import sys

from dateutil.relativedelta import relativedelta

import discord
from discord.ext import commands
import os

intents = discord.Intents.default()

intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix='/',
    intents=intents,
    help_command=None
)


@bot.hybrid_command(name="joined", description="Показывает стаж пользователя")
async def get_join_date(ctx, member: discord.Member = None):
    target = member or ctx.author

    if not target.joined_at:
        return await ctx.send("Данные недоступны")

    now = datetime.datetime.now(target.joined_at.tzinfo)
    delta = relativedelta(now, target.joined_at)

    highest_role = target.roles[-1]

    embed = discord.Embed(
        title=f"Статистика {target.display_name}",
        description=(
            f"**На сервере:**\n"
            f"лет: {delta.years}, месяцев: {delta.months}, дней: {delta.days}, часов: {delta.hours}, минут: {delta.months}, секунд: {delta.seconds}\n"
            f"**Точное время:**\n"
            f"{target.joined_at.strftime('%d.%m.%Y %H:%M:%S %Z')}\n"
            f"**Роль:**\n"
            f"{highest_role.name}"
        ),
        color=highest_role.color
    )

    await ctx.send(embed=embed)


@bot.hybrid_command(name="list_roles", description="Показывает все роли сервера")
async def list_roles(ctx):
    """Показать все роли сервера"""
    guild = ctx.guild
    all_roles = [role.name for role in guild.roles]

    unused_roles = await find_unused_roles(guild)

    embed = discord.Embed(title="Список ролей", color=0x00ff00)
    embed.add_field(name="количество", value=str(len(all_roles)), inline=False)
    embed.add_field(name="Все роли", value="\n".join(all_roles) or "Нет", inline=False)
    embed.add_field(name="Неиспользуемые", value="\n".join(unused_roles) or "Нет", inline=False)

    await ctx.send(embed=embed)


@bot.hybrid_command(name="stop_bot", description="Stop bot_core executing")
@commands.is_owner()
async def stop_bot(ctx):
    await ctx.send("Бот завершает работу")
    sys.exit(0)


@bot.hybrid_command(name="ping")
async def ping(ctx):
    await ctx.send("Pong! 🏓")


@bot.event
async def on_member_join(member):
    print("member joined ", member)
    channel = member.guild.system_channel
    await channel.send(f"Добро пожаловать, {member.mention}!")


@bot.event
async def on_message(message):
    t = message.content.lower()
    print("message sent ", t, message)
    if "спасибо" in t:
        await message.add_reaction('❤️')


async def find_unused_roles(guild):
    used_roles = set()
    for member in guild.members:
        used_roles.update(member.roles)

    return [role.name for role in guild.roles
            if role not in used_roles
            and not role.managed
            and role != guild.default_role]


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Бот {bot.user} готов!')


bot.run(os.getenv("GUARD_BOT_API_KEY"))

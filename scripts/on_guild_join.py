import discord
from loguru import logger

from bot import GuardBot, GuardDatabase


async def main(bot: GuardBot, guild: discord.Guild):
    await GuardDatabase.save_server(guild.id, guild.name)

    await GuardDatabase.save_template(
        guild.id,
        "greetings_list",
        ""
        "➕ Бобро поржаловать, {member.mention}!\\"
        "➕ Встречайте: {member.mention}\\"
        "➕ Дарова, {member.mention}\\"
        "➕ У нас новый бибус: {member.mention}\\"
        "➕ Коничива: {member.mention}"
    )

    await GuardDatabase.save_template(
        guild.id,
        "join_message_title",
        "**Добро пожаловать на {member.guild.name}!**"
    )
    await GuardDatabase.save_template(
        guild.id,
        "join_message_description",
        """
    {member.mention}, рады видеть тебя на нашем сервере {member.guild.name}!
Это сервер для всех, кто любит компы, люди, которые хотят пообщаться, геймеры и даже программисты.

    Я, {member.guild.me.mention}, помогаю администраторам и не только на сервере.
Пройдись по путеводителю и прочитай все правила, не забудь зарегистрироваться в соответствующем канале.

    Можешь почитать или поспрашивать других пользователей о том, что я умею. К сожалению Я сейчас в разработке
и парой могу нести чушь или сделать что-то, не так.
"""
    )
    await GuardDatabase.save_template(
        guild.id,
        "join_message_footer",
        "Photo by @protokops. Member #{member.guild.member_count}"
    )

    logger.success(f"init bot deps for {guild.name}")

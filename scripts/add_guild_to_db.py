import discord
from loguru import logger

from bot import GuardBot


async def main(*, bot: GuardBot, interaction: discord.Interaction):
    guild = interaction.guild
    await bot.db.save_server(
        guild.id,
        guild.name,
        is_active=True,
        voice_channel_announce=1371207588045262868
    )

    await bot.db.save_template(
        guild.id,
        "greetings_list",
        ""
        "➕ Бобро поржаловать, {member.mention}!\\"
        "➕ Встречайте: {member.mention}\\"
        "➕ Дарова, {member.mention}\\"
        "➕ У нас новый бибус: {member.mention}\\"
        "➕ Коничива: {member.mention}"
    )

    await interaction.channel.send(f"Guild: {guild.name} added to DataBase")

    await bot.db.save_template(
        guild.id,
        "join_message_title",
        "**Добро пожаловать на {member.guild.name}!**"
    )
    await bot.db.save_template(
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
    await bot.db.save_template(
        guild.id,
        "join_message_footer",
        "Photo by @protokops. Member #{member.guild.member_count}"
    )

    await interaction.channel.send("Templates added to DataBase")

    logger.success(f"init bot deps for {guild.name}")

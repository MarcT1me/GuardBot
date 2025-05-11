import random

import discord
from bot import GuardBot, GuardDatabase


async def main(bot: GuardBot, *, member: discord.Member):
    if member.bot: return

    server: GuardDatabase.server = await GuardDatabase.get_server(member.guild.id)

    if system_channel := member.guild.system_channel:
        await system_channel.send("||➕||")
        greetings_list_template: GuardDatabase.template = await GuardDatabase.get_template(
            server,
            "greetings_list"
        )
        greetings = random.choice(greetings_list_template.content.split("\\"))
        await system_channel.send(
            greetings.format(member=member)
            # f"➕ Бобро поржаловать, {member.mention}!"
        )

    title: GuardDatabase.template = await GuardDatabase.get_template(
        server,
        "join_message_title"
    )
    description: GuardDatabase.template = await GuardDatabase.get_template(
        server,
        "join_message_description"
    )
    footer: GuardDatabase.template = await GuardDatabase.get_template(
        server,
        "join_message_footer"
    )

    embed = discord.Embed(
        title=title.content.format(member=member),
        # f"**Добро пожаловать на {member.guild.name}!**",
        description=description.content.format(member=member),
        # f" {member.mention}, рады видеть тебя на нашем сервере {member.guild.name}!\n"
        # f"Это сервер для всех, кто любит компы, люди, которые хотят пообщаться, геймеры и даже программисты.\n"
        # f"\n"
        # f"Я, {member.guild.me.mention}, помогаю администраторам и не только на сервере. "
        # f"Пройдись по путеводителю и прочитай все правила, не забудь зарегистрироваться в соответствующем канале.\n"
        # f"\n"
        # f"Можешь почитать или поспрашивать других пользователей о том, что я умею. К сожалению Я сейчас в разработке"
        # f"и парой могу нести чушь или сделать что-то, не так.",
        color=0xDE7A22
    )

    embed.set_thumbnail(url=member.guild.icon.url)

    embed.set_image(url="attachment://welcome_ByPROtoKOPs.png")

    # Добавляем футер
    embed.set_footer(
        text=footer.content.format(member=member)
        # f"Photo by @protokops. Member #{member.guild.member_count}"
    )

    await member.send(
        embed=embed,
        file=discord.File("assets/welcome_ByPROtoKOPs.png", filename="welcome_ByPROtoKOPs.png")
    )

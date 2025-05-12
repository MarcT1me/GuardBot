import random

import discord
from bot import GuardBot


async def main(*, bot: GuardBot, member: discord.Member = None, member_id: int = None, **kwargs):
    if member.bot: return  # ignore bot adding

    if member_id is not None:  # if member specified as ID - use member for guild and member_id for search target member
        for member in member.guild.members:
            if member.id == member_id:
                break

    server: bot.db.server = await bot.db.get_server(member.guild.id)

    if system_channel := member.guild.system_channel:
        greetings_list_template: bot.db.template = await bot.db.get_template(
            server,
            "greetings_list"
        )
        greetings = random.choice(greetings_list_template.content.split("\\"))
        await system_channel.send(
            greetings.format(member=member)
        )

    title: bot.db.template = await bot.db.get_template(
        server,
        "join_message_title"
    )
    description: bot.db.template = await bot.db.get_template(
        server,
        "join_message_description"
    )
    footer: bot.db.template = await bot.db.get_template(
        server,
        "join_message_footer"
    )

    embed = discord.Embed(
        title=title.content.format(member=member),
        description=description.content.format(member=member),
        color=0xDE7A22
    )

    embed.set_thumbnail(url=member.guild.icon.url)

    embed.set_image(url="attachment://welcome_ByPROtoKOPs.png")

    # Добавляем футер
    embed.set_footer(
        text=footer.content.format(member=member)
    )

    await member.send(
        embed=embed,
        file=discord.File("assets/welcome_ByPROtoKOPs.png", filename="welcome_ByPROtoKOPs.png")
    )
